import { spawn, type ChildProcess } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { DEFAULT_SOCKET_PATH } from './transport/socket-client';

interface DaemonManagerOptions {
  socketPath?: string;
  repoRoot?: string;
  maxWaitMs?: number;
  retryIntervalMs?: number;
}

let daemonProcess: ChildProcess | null = null;
let isManagedDaemon = false;

/**
 * Check if the daemon UNIX socket is actively listening and responsive.
 */
export function isSocketAlive(socketPath: string = DEFAULT_SOCKET_PATH): Promise<boolean> {
  return new Promise((resolve) => {
    const client = net.createConnection(socketPath);
    const timer = setTimeout(() => {
      client.destroy();
      resolve(false);
    }, 400);

    client.on('connect', () => {
      clearTimeout(timer);
      client.end();
      resolve(true);
    });

    client.on('error', () => {
      clearTimeout(timer);
      resolve(false);
    });
  });
}

/**
 * Find the repository root containing pyproject.toml.
 */
export function findRepoRoot(): string {
  const currentFileDir = path.dirname(fileURLToPath(import.meta.url));
  const startPaths = [
    process.cwd(),
    currentFileDir,
  ];

  for (const start of startPaths) {
    let curr = path.resolve(start);
    for (let i = 0; i < 5; i++) {
      if (fs.existsSync(path.join(curr, 'pyproject.toml'))) {
        return curr;
      }
      const parent = path.dirname(curr);
      if (parent === curr) break;
      curr = parent;
    }
  }

  return process.cwd();
}

/**
 * Ensure the Python daemon is running.
 * If already active, adopts it (no-op).
 * If absent, spawns `uv run ekko daemon` and polls until socket accepts connections.
 */
export async function ensureDaemonRunning(options: DaemonManagerOptions = {}): Promise<boolean> {
  const socketPath = options.socketPath || DEFAULT_SOCKET_PATH;
  const maxWaitMs = options.maxWaitMs || 5000;
  const retryIntervalMs = options.retryIntervalMs || 150;
  const repoRoot = options.repoRoot || findRepoRoot();

  // 1. Test existing socket connectivity
  const alreadyRunning = await isSocketAlive(socketPath);
  if (alreadyRunning) {
    console.log('[DaemonManager] Daemon préexistant détecté et actif sur', socketPath);
    isManagedDaemon = false;
    return true;
  }

  // Clean stale socket file if process is dead
  if (fs.existsSync(socketPath)) {
    try {
      fs.unlinkSync(socketPath);
    } catch {
      // ignore
    }
  }

  console.log('[DaemonManager] Démarrage automatique du daemon Ekko depuis', repoRoot);

  // Determine PATH including ~/.local/bin where uv typically resides
  const homeDir = process.env.HOME || '/home/mohamed';
  const customPath = `${homeDir}/.local/bin:${process.env.PATH || ''}`;

  let uvBin = 'uv';
  if (fs.existsSync(`${homeDir}/.local/bin/uv`)) {
    uvBin = `${homeDir}/.local/bin/uv`;
  }

  daemonProcess = spawn(uvBin, ['run', 'ekko', 'daemon'], {
    cwd: repoRoot,
    env: {
      ...process.env,
      PATH: customPath,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  isManagedDaemon = true;

  daemonProcess.stdout?.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.trim()) {
        console.log(`[ekko-daemon] ${line}`);
      }
    }
  });

  daemonProcess.stderr?.on('data', (data) => {
    const lines = data.toString().split('\n');
    for (const line of lines) {
      if (line.trim()) {
        console.error(`[ekko-daemon:ERR] ${line}`);
      }
    }
  });

  daemonProcess.on('error', (err) => {
    console.error('[DaemonManager:ERR] Erreur lors du lancement du processus daemon:', err);
    daemonProcess = null;
    isManagedDaemon = false;
  });

  daemonProcess.on('exit', (code, signal) => {
    console.log(`[DaemonManager] Processus daemon terminé (code: ${code}, signal: ${signal})`);
    daemonProcess = null;
    isManagedDaemon = false;
  });

  // 2. Active polling until socket accepts connections
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    await new Promise((res) => setTimeout(res, retryIntervalMs));
    const alive = await isSocketAlive(socketPath);
    if (alive) {
      console.log(`[DaemonManager] Daemon opérationnel et socket connecté après ${Date.now() - start}ms`);
      return true;
    }
  }

  console.warn(`[DaemonManager:WARN] Timeout (${maxWaitMs}ms) en attente du socket daemon.`);
  return false;
}

/**
 * Graceful termination of the managed daemon.
 * Sends SIGTERM, waits, and forces SIGKILL after timeout.
 */
export async function stopDaemonIfManaged(): Promise<void> {
  if (!isManagedDaemon || !daemonProcess || daemonProcess.killed) {
    return;
  }

  console.log('[DaemonManager] Arrêt gracieux du daemon managé (SIGTERM)...');
  const proc = daemonProcess;
  daemonProcess = null;
  isManagedDaemon = false;

  return new Promise<void>((resolve) => {
    let killTimer: NodeJS.Timeout | null = null;

    const onExit = () => {
      if (killTimer) clearTimeout(killTimer);
      resolve();
    };

    proc.once('exit', onExit);

    // Fallback SIGKILL after 3000ms
    killTimer = setTimeout(() => {
      console.warn('[DaemonManager:WARN] Forçage de l\'arrêt du daemon (SIGKILL)...');
      try {
        proc.kill('SIGKILL');
      } catch {
        // ignore
      }
      resolve();
    }, 3000);

    try {
      proc.kill('SIGTERM');
    } catch {
      resolve();
    }
  });
}

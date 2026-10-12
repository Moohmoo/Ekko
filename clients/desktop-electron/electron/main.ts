import { app, BrowserWindow, ipcMain, screen } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sendJsonRpc, streamPrompt } from './transport/socket-client';

import fs from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

process.env.DIST = path.join(__dirname, '../dist');
process.env.VITE_PUBLIC = app.isPackaged
  ? process.env.DIST
  : path.join(__dirname, '../public');

let win: BrowserWindow | null = null;
const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL'];

function getPreloadPath(): string {
  // 1. Production / compiled path (same directory as main.js)
  const prodPath = path.join(__dirname, 'preload.cjs');
  if (fs.existsSync(prodPath)) {
    console.log('[Main] Using production preload path:', prodPath);
    return prodPath;
  }

  // 2. Dev path relative to electron/ source directory
  const devPath = path.join(__dirname, '../dist-electron/preload.cjs');
  if (fs.existsSync(devPath)) {
    console.log('[Main] Using dev relative preload path:', devPath);
    return devPath;
  }

  // 3. Absolute project root fallback
  const fallbackPath = path.resolve(app.getAppPath(), 'dist-electron/preload.cjs');
  console.log('[Main] Using fallback preload path:', fallbackPath);
  return fallbackPath;
}

function getCenteredTopBounds(width: number, height: number) {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { x: workX, y: workY, width: workWidth } = primaryDisplay.workArea;

  return {
    x: Math.round(workX + (workWidth - width) / 2),
    y: workY, // Anchored to top work area (under panel on Linux/GNOME, y=0 on Windows)
    width,
    height,
  };
}

function createWindow() {
  const podWidth = 620;
  const podHeight = 230;
  const initialBounds = getCenteredTopBounds(podWidth, podHeight);

  const preloadPath = getPreloadPath();

  win = new BrowserWindow({
    width: initialBounds.width,
    height: initialBounds.height,
    x: initialBounds.x,
    y: initialBounds.y,
    resizable: false,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: false,
    hasShadow: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: preloadPath,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false, // Essential to allow require('electron') in preload.cjs
    },
  });

  // Explicit preload-error listener for terminal observability
  win.webContents.on('preload-error', (_event, preloadErrPath, error) => {
    console.error('[Main:FATAL] Preload execution error in:', preloadErrPath);
    console.error(error);
  });

  // Native keyboard shortcut fallback for closing window (Escape or Ctrl+Q)
  win.webContents.on('before-input-event', (_event, input) => {
    if (input.key === 'Escape' || (input.control && input.key.toLowerCase() === 'q')) {
      console.log('[Main] Escape/Ctrl+Q pressed, closing window.');
      win?.close();
    }
  });

  // Automatically open detached DevTools in dev mode
  if (process.env.NODE_ENV !== 'production' || !app.isPackaged) {
    win.webContents.openDevTools({ mode: 'detach' });
  }

  if (VITE_DEV_SERVER_URL) {
    console.log('[Main] Loading dev server URL:', VITE_DEV_SERVER_URL);
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    console.log('[Main] Loading static index.html from:', process.env.DIST);
    win.loadFile(path.join(process.env.DIST!, 'index.html'));
  }

  // Auto-hide on blur (optional click outside dismiss)
  win.on('blur', () => {
    // Keep window visible or allow user to toggle
  });
}

// State tracker for daemon connectivity transitions
let isDaemonConnected: boolean | null = null;

// IPC Handlers
ipcMain.handle('daemon:ping', async () => {
  try {
    const res = await sendJsonRpc<{ status: string; timestamp: string }>('ping');
    if (isDaemonConnected !== true) {
      isDaemonConnected = true;
      console.log('[Daemon] Connecté au socket local /tmp/ekko.sock');
    }
    return res;
  } catch (err) {
    if (isDaemonConnected !== false) {
      isDaemonConnected = false;
      console.warn('[Daemon:WARN] Liaison perdue avec le daemon');
    }
    return null;
  }
});

ipcMain.handle('daemon:get_notes', async () => {
  try {
    return await sendJsonRpc<unknown[]>('scan_notes', { limit: 20 });
  } catch (_e) {
    return await sendJsonRpc<unknown[]>('scan_inbox', { limit: 20 });
  }
});

ipcMain.handle('daemon:ingest_file', async (_event, filePath: string) => {
  return await sendJsonRpc<{ status: string; note: { id: string; title: string; slug: string; summary: string } }>(
    'ingest_file',
    { file_path: filePath }
  );
});

ipcMain.handle('daemon:get_pending_signals', async () => {
  return await sendJsonRpc<{ signals: unknown[]; total_count: number }>('get_pending_signals', { limit: 20 });
});

ipcMain.handle(
  'daemon:resolve_signal',
  async (_event, { signalId, action }: { signalId: string; action: 'archive' | 'discard' }) => {
    return await sendJsonRpc<{ status: string; signal_id: string; action: string }>(
      'resolve_signal',
      { signal_id: signalId, action }
    );
  }
);

ipcMain.handle(
  'daemon:resolve_all_pending_signals',
  async (_event, { action }: { action: 'archive' | 'discard' }) => {
    return await sendJsonRpc<{ status: string; action: string; count: number }>(
      'resolve_all_pending_signals',
      { action }
    );
  }
);

ipcMain.handle('daemon:submit_prompt', async (event, prompt: string) => {
  return await new Promise((resolve, reject) => {
    streamPrompt(
      prompt,
      (chunk) => {
        event.sender.send('daemon:prompt_chunk', chunk);
      },
      (full) => {
        resolve(full);
      },
      (err) => {
        reject(new Error(err));
      }
    );
  });
});

ipcMain.handle('window:close', () => {
  if (win) {
    win.close();
  }
});

ipcMain.handle('window:resize', async (_event, { width, height }: { width: number; height: number }) => {
  if (win && !win.isDestroyed()) {
    const display = screen.getDisplayMatching(win.getBounds());
    const { x: workX, y: workY, width: workWidth } = display.workArea;
    const newX = Math.round(workX + (workWidth - width) / 2);
    const newY = workY;

    win.setBounds({ x: newX, y: newY, width, height }, true);
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
    win = null;
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.whenReady().then(createWindow);

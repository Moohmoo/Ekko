import { app, BrowserWindow, globalShortcut, ipcMain, Menu, screen, shell, Tray } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sendJsonRpc, streamPrompt, subscribeDaemonEvents } from './transport/socket-client';

import fs from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

process.env.DIST = path.join(__dirname, '../dist');
process.env.VITE_PUBLIC = app.isPackaged
  ? process.env.DIST
  : path.join(__dirname, '../public');

// Hardware acceleration & GPU rasterization optimizations for Linux/Chromium
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');

let win: BrowserWindow | null = null;
let tray: Tray | null = null;
let isQuitting = false;
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

function toggleWindow() {
  if (!win || win.isDestroyed()) return;

  if (win.isVisible()) {
    win.hide();
  } else {
    // Re-verify centering in case display geometry changed while hidden
    const [currentWidth, currentHeight] = win.getSize();
    const bounds = getCenteredTopBounds(currentWidth, currentHeight);
    win.setPosition(bounds.x, bounds.y);
    win.show();
    win.focus();
  }
}

function getTrayIconPath(state: 'idle' | 'ingesting' | 'alert' | 'error' | 'offline'): string {
  const publicDir = process.env.VITE_PUBLIC || path.join(__dirname, '../public');
  switch (state) {
    case 'ingesting':
      return path.join(publicDir, 'assets/tray-ingest.png');
    case 'alert':
      return path.join(publicDir, 'assets/tray-alert.png');
    case 'offline':
      return path.join(publicDir, 'assets/tray-offline.png');
    case 'idle':
    default:
      return path.join(publicDir, 'assets/tray-idle.png');
  }
}

function updateTrayIcon(state: 'idle' | 'ingesting' | 'alert' | 'error' | 'offline') {
  if (!tray || tray.isDestroyed()) return;
  const iconPath = getTrayIconPath(state);
  if (fs.existsSync(iconPath)) {
    tray.setImage(iconPath);
  }
}

function createTray() {
  const iconPath = getTrayIconPath('idle');
  tray = new Tray(iconPath);
  tray.setToolTip('Ekko - Ambient Cognitive Buffer');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Afficher / Masquer Ekko',
      click: () => toggleWindow(),
    },
    { type: 'separator' },
    {
      label: 'Quitter Ekko',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('click', () => toggleWindow());
}

function createWindow() {
  const windowWidth = 660; // 620px notch core + 2x20px transparent side margin for fillets
  const podHeight = 230;
  const initialBounds = getCenteredTopBounds(windowWidth, podHeight);

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
    skipTaskbar: true,
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

  // Native keyboard shortcuts: Escape to hide, Ctrl+Q to quit
  win.webContents.on('before-input-event', (_event, input) => {
    if (input.key === 'Escape') {
      win?.hide();
    } else if (input.control && input.key.toLowerCase() === 'q') {
      console.log('[Main] Ctrl+Q pressed, quitting application.');
      isQuitting = true;
      app.quit();
    }
  });

  // Hide rather than destroy window when user closes it
  win.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      win?.hide();
    }
  });

  // Automatically open detached DevTools in dev mode (except in automated E2E tests)
  if (!process.env.E2E_TEST && (process.env.NODE_ENV !== 'production' || !app.isPackaged)) {
    win.webContents.openDevTools({ mode: 'detach' });
  }

  if (VITE_DEV_SERVER_URL) {
    console.log('[Main] Loading dev server URL:', VITE_DEV_SERVER_URL);
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    console.log('[Main] Loading static index.html from:', process.env.DIST);
    win.loadFile(path.join(process.env.DIST!, 'index.html'));
  }
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
    return await sendJsonRpc<unknown[]>('scan_notes', { limit: 50 });
  } catch (_e) {
    return await sendJsonRpc<unknown[]>('scan_inbox', { limit: 50 });
  }
});

ipcMain.handle(
  'daemon:search_notes',
  async (
    _event,
    {
      query,
      mode = 'hybrid',
      limit = 20,
    }: { query: string; mode?: 'hybrid' | 'lexical' | 'semantic'; limit?: number }
  ) => {
    return await sendJsonRpc<unknown[]>('search_notes', { query, mode, limit });
  }
);

ipcMain.handle('shell:open_external', async (_event, url: string) => {
  if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
    await shell.openExternal(url);
  }
});

const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

ipcMain.handle('daemon:ingest_file', async (_event, filePath: string) => {
  try {
    const stats = fs.statSync(filePath);
    if (stats.size > MAX_FILE_SIZE_BYTES) {
      return {
        status: 'rejected',
        reason: 'file_too_large',
        message: `Fichier trop volumineux (${stats.size} octets > ${MAX_FILE_SIZE_BYTES} octets max).`,
        max_bytes: MAX_FILE_SIZE_BYTES,
      };
    }
  } catch (err) {
    // If stat fails, continue and let daemon return proper error
  }

  return await sendJsonRpc<{ status: string; filename?: string; message?: string; note?: { id: string; title: string; slug: string; summary: string } }>(
    'ingest_file',
    { file_path: filePath }
  );
});

ipcMain.handle('daemon:ingest_url', async (_event, url: string) => {
  return await sendJsonRpc<{ status: string; filename?: string; url?: string; message?: string; note?: { id: string; title: string; slug: string; summary: string } }>(
    'ingest_url',
    { url }
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

ipcMain.handle('daemon:submit_prompt', async (event, prompt: string, sessionId?: string) => {
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
      },
      (toolEvent) => {
        event.sender.send('daemon:tool_event', toolEvent);
      },
      sessionId || 'desktop_electron'
    );
  });
});

ipcMain.handle('chat:send_message', async (event, { prompt }: { prompt: string; history?: unknown[] }) => {
  return await new Promise((resolve, reject) => {
    streamPrompt(
      prompt,
      (chunk) => {
        event.sender.send('chat:token', chunk);
      },
      (full) => {
        event.sender.send('chat:done');
        resolve(full);
      },
      (err) => {
        event.sender.send('chat:error', err);
        reject(new Error(err));
      },
      undefined,
      'desktop_chat'
    );
  });
});

ipcMain.handle('daemon:get_system_settings', async () => {
  return await sendJsonRpc('get_system_settings');
});

ipcMain.handle('daemon:update_user_context', async (_event, context: Record<string, unknown>) => {
  return await sendJsonRpc('update_user_context', context);
});

ipcMain.handle('daemon:update_sources', async (_event, sources: unknown[]) => {
  return await sendJsonRpc('update_sources', { sources });
});

ipcMain.handle('tray:set_state', async (_event, state: 'idle' | 'ingesting' | 'alert' | 'error') => {
  updateTrayIcon(state);
});

ipcMain.handle('window:close', () => {
  if (win && !win.isDestroyed()) {
    win.hide();
  }
});

ipcMain.handle('window:resize', async (_event, { width, height }: { width: number; height: number }) => {
  if (win && !win.isDestroyed()) {
    const bounds = getCenteredTopBounds(width, height);
    win.setBounds(bounds);
  }
});

ipcMain.on('dev:test_mascot_emotion', (_event, emotion: string | null) => {
  if (win && !win.isDestroyed()) {
    win.webContents.send('dev:set_mascot_emotion', emotion);
  }
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
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
  } else if (win) {
    win.show();
    win.focus();
  }
});

app.whenReady().then(() => {
  createWindow();
  createTray();

  // Subscribe to daemon push notifications (e.g. instant note completion)
  subscribeDaemonEvents((method, params) => {
    if (win && !win.isDestroyed()) {
      win.webContents.send(method, params);
    }
  });

  // Register global shortcut to toggle window
  const shortcutRegistered = globalShortcut.register('CommandOrControl+Shift+Space', () => {
    toggleWindow();
  });
  if (!shortcutRegistered) {
    console.warn('[Main:WARN] Global shortcut CommandOrControl+Shift+Space registration failed.');
  }

  // Recalculate notch position if display resolution or work area changes
  screen.on('display-metrics-changed', () => {
    if (win && !win.isDestroyed()) {
      const [width, height] = win.getSize();
      const bounds = getCenteredTopBounds(width, height);
      win.setPosition(bounds.x, bounds.y);
    }
  });
});

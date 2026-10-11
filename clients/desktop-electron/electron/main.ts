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

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth } = primaryDisplay.workAreaSize;
  const podWidth = 440;
  const podHeight = 560;

  // Position anchored in top right with 20px margins
  const posX = Math.max(20, screenWidth - podWidth - 20);
  const posY = 30;

  const preloadPath = getPreloadPath();

  win = new BrowserWindow({
    width: podWidth,
    height: podHeight,
    x: posX,
    y: posY,
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

// IPC Handlers
ipcMain.handle('daemon:ping', async () => {
  console.log('[Main] Received daemon:ping invocation from renderer');
  const res = await sendJsonRpc<{ status: string; timestamp: string }>('ping');
  console.log('[Main] Returning daemon:ping result to renderer:', res);
  return res;
});

ipcMain.handle('daemon:get_notes', async () => {
  return await sendJsonRpc<unknown[]>('scan_inbox', { limit: 20 });
});

ipcMain.handle('daemon:ingest_file', async (_event, filePath: string) => {
  const prompt = `Analyse et indexe ce document déposé : ${filePath}`;
  return await new Promise((resolve, reject) => {
    streamPrompt(
      prompt,
      () => {},
      (res) => resolve(res),
      (err) => reject(new Error(err))
    );
  });
});

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

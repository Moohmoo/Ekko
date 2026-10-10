import { app, BrowserWindow, ipcMain, screen } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sendJsonRpc, streamPrompt } from './ipc-bridge';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

process.env.DIST = path.join(__dirname, '../dist');
process.env.VITE_PUBLIC = app.isPackaged
  ? process.env.DIST
  : path.join(__dirname, '../public');

let win: BrowserWindow | null = null;
const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL'];

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth } = primaryDisplay.workAreaSize;
  const podWidth = 440;
  const podHeight = 560;

  // Position anchored in top right with 20px margins
  const posX = Math.max(20, screenWidth - podWidth - 20);
  const posY = 30;

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
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

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

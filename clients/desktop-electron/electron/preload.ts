import { contextBridge, ipcRenderer, webUtils } from 'electron';

export interface EkkoAPI {
  ping: () => Promise<{ status: string; timestamp: string } | null>;
  getNotes: () => Promise<unknown[]>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<{ status: string; note?: { id: string; title: string; slug: string; summary: string; source?: string } }>;
  getDroppedFilePath: (file: File) => string;
  closeWindow: () => Promise<void>;
  resizeWindow: (width: number, height: number) => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

const api: EkkoAPI = {
  ping: () => ipcRenderer.invoke('daemon:ping'),
  getNotes: () => ipcRenderer.invoke('daemon:get_notes'),
  submitPrompt: (prompt: string) => ipcRenderer.invoke('daemon:submit_prompt', prompt),
  ingestFile: (filePath: string) => ipcRenderer.invoke('daemon:ingest_file', filePath),
  getDroppedFilePath: (file: File) => {
    try {
      return webUtils.getPathForFile(file);
    } catch (err) {
      console.error('[Preload] Échec webUtils.getPathForFile:', err);
      return '';
    }
  },
  closeWindow: () => ipcRenderer.invoke('window:close'),
  resizeWindow: (width: number, height: number) => ipcRenderer.invoke('window:resize', { width, height }),
  onPromptChunk: (callback: (chunk: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, chunk: string) => callback(chunk);
    ipcRenderer.on('daemon:prompt_chunk', handler);
    return () => {
      ipcRenderer.removeListener('daemon:prompt_chunk', handler);
    };
  },
};

contextBridge.exposeInMainWorld('ekkoAPI', api);

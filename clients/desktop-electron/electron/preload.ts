import { contextBridge, ipcRenderer } from 'electron';

export interface EkkoAPI {
  ping: () => Promise<{ status: string; timestamp: string }>;
  getNotes: () => Promise<unknown[]>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<string>;
  closeWindow: () => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

const api: EkkoAPI = {
  ping: () => ipcRenderer.invoke('daemon:ping'),
  getNotes: () => ipcRenderer.invoke('daemon:get_notes'),
  submitPrompt: (prompt: string) => ipcRenderer.invoke('daemon:submit_prompt', prompt),
  ingestFile: (filePath: string) => ipcRenderer.invoke('daemon:ingest_file', filePath),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  onPromptChunk: (callback: (chunk: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, chunk: string) => callback(chunk);
    ipcRenderer.on('daemon:prompt_chunk', handler);
    return () => {
      ipcRenderer.removeListener('daemon:prompt_chunk', handler);
    };
  },
};

contextBridge.exposeInMainWorld('ekkoAPI', api);

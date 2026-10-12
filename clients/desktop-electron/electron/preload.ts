import { contextBridge, ipcRenderer, webUtils } from 'electron';

export interface Signal {
  id: string;
  title: string;
  source_type: string;
  source_url: string;
  summary: string;
  created_at: string;
}

export interface SignalsResult {
  signals: Signal[];
  total_count: number;
}

export interface EkkoAPI {
  ping: () => Promise<{ status: string; timestamp: string } | null>;
  getNotes: () => Promise<unknown[]>;
  getPendingSignals: () => Promise<SignalsResult | Signal[]>;
  resolveSignal: (signalId: string, action: 'archive' | 'discard') => Promise<{ status: string; signal_id?: string; action?: string }>;
  resolveAllPendingSignals: (action: 'archive' | 'discard') => Promise<{ status: string; action?: string; count?: number }>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<{ status: string; filename?: string; message?: string; note?: { id: string; title: string; slug: string; summary: string; source?: string } }>;
  getDroppedFilePath: (file: File) => string;
  closeWindow: () => Promise<void>;
  resizeWindow: (width: number, height: number) => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

const api: EkkoAPI = {
  ping: () => ipcRenderer.invoke('daemon:ping'),
  getNotes: () => ipcRenderer.invoke('daemon:get_notes'),
  getPendingSignals: () => ipcRenderer.invoke('daemon:get_pending_signals'),
  resolveSignal: (signalId: string, action: 'archive' | 'discard') =>
    ipcRenderer.invoke('daemon:resolve_signal', { signalId, action }),
  resolveAllPendingSignals: (action: 'archive' | 'discard') =>
    ipcRenderer.invoke('daemon:resolve_all_pending_signals', { action }),
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

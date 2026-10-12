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

export interface IngestResult {
  status: string;
  filename?: string;
  url?: string;
  message?: string;
  reason?: string;
  content_hash?: string;
  max_bytes?: number;
  note?: { id: string; title: string; slug: string; summary: string; source?: string };
}

export interface EkkoAPI {
  ping: () => Promise<{ status: string; timestamp: string } | null>;
  getNotes: () => Promise<unknown[]>;
  searchNotes: (query: string, options?: { mode?: 'hybrid' | 'lexical' | 'semantic'; limit?: number }) => Promise<unknown[]>;
  getPendingSignals: () => Promise<SignalsResult | Signal[]>;
  resolveSignal: (signalId: string, action: 'archive' | 'discard') => Promise<{ status: string; signal_id?: string; action?: string }>;
  resolveAllPendingSignals: (action: 'archive' | 'discard') => Promise<{ status: string; action?: string; count?: number }>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<IngestResult>;
  ingestUrl: (url: string) => Promise<IngestResult>;
  getDroppedFilePath: (file: File) => string;
  openExternal: (url: string) => Promise<void>;
  closeWindow: () => Promise<void>;
  resizeWindow: (width: number, height: number) => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
  onToolEvent: (callback: (event: any) => void) => () => void;
}

const api: EkkoAPI = {
  ping: () => ipcRenderer.invoke('daemon:ping'),
  getNotes: () => ipcRenderer.invoke('daemon:get_notes'),
  searchNotes: (query: string, options?: { mode?: 'hybrid' | 'lexical' | 'semantic'; limit?: number }) =>
    ipcRenderer.invoke('daemon:search_notes', { query, ...options }),
  getPendingSignals: () => ipcRenderer.invoke('daemon:get_pending_signals'),
  resolveSignal: (signalId: string, action: 'archive' | 'discard') =>
    ipcRenderer.invoke('daemon:resolve_signal', { signalId, action }),
  resolveAllPendingSignals: (action: 'archive' | 'discard') =>
    ipcRenderer.invoke('daemon:resolve_all_pending_signals', { action }),
  submitPrompt: (prompt: string) => ipcRenderer.invoke('daemon:submit_prompt', prompt),
  ingestFile: (filePath: string) => ipcRenderer.invoke('daemon:ingest_file', filePath),
  ingestUrl: (url: string) => ipcRenderer.invoke('daemon:ingest_url', url),
  getDroppedFilePath: (file: File) => {
    try {
      return webUtils.getPathForFile(file);
    } catch (err) {
      console.error('[Preload] Échec webUtils.getPathForFile:', err);
      return '';
    }
  },
  openExternal: (url: string) => ipcRenderer.invoke('shell:open_external', url),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  resizeWindow: (width: number, height: number) => ipcRenderer.invoke('window:resize', { width, height }),
  onPromptChunk: (callback: (chunk: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, chunk: string) => callback(chunk);
    ipcRenderer.on('daemon:prompt_chunk', handler);
    return () => {
      ipcRenderer.removeListener('daemon:prompt_chunk', handler);
    };
  },
  onToolEvent: (callback: (event: any) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, eventData: any) => callback(eventData);
    ipcRenderer.on('daemon:tool_event', handler);
    return () => {
      ipcRenderer.removeListener('daemon:tool_event', handler);
    };
  },
};

contextBridge.exposeInMainWorld('ekkoAPI', api);

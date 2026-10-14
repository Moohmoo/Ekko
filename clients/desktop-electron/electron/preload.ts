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
  submitPrompt: (prompt: string, sessionId?: string) => Promise<string>;
  getSystemSettings: () => Promise<unknown>;
  updateUserContext: (context: unknown) => Promise<unknown>;
  updateSources: (sources: unknown[]) => Promise<unknown>;
  ingestFile: (filePath: string) => Promise<IngestResult>;
  ingestUrl: (url: string) => Promise<IngestResult>;
  getDroppedFilePath: (file: File) => string;
  openExternal: (url: string) => Promise<void>;
  closeWindow: () => Promise<void>;
  resizeWindow: (width: number, height: number) => Promise<void>;
  setTrayState: (state: 'idle' | 'ingesting' | 'alert' | 'error') => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
  onToolEvent: (callback: (event: any) => void) => () => void;
  onNoteCreated: (callback: (note: any) => void) => () => void;
  testMascotEmotion: (emotion: string | null) => void;
  cycleAllEmotions: () => Promise<void>;
  onTestMascotEmotion: (callback: (emotion: string | null) => void) => () => void;
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
  submitPrompt: (prompt: string, sessionId?: string) =>
    ipcRenderer.invoke('daemon:submit_prompt', prompt, sessionId),
  getSystemSettings: () => ipcRenderer.invoke('daemon:get_system_settings'),
  updateUserContext: (context: unknown) =>
    ipcRenderer.invoke('daemon:update_user_context', context),
  updateSources: (sources: unknown[]) =>
    ipcRenderer.invoke('daemon:update_sources', sources),
  ingestFile: (filePath: string) => ipcRenderer.invoke('daemon:ingest_file', filePath),
  ingestUrl: (url: string) => ipcRenderer.invoke('daemon:ingest_url', url),
  getDroppedFilePath: (file: File) => {
    try {
      const p = webUtils.getPathForFile(file);
      if (p) return p;
    } catch {
      // ignore webUtils error
    }
    try {
      const legacy = (file as unknown as { path?: string }).path;
      if (typeof legacy === 'string' && legacy) {
        return legacy;
      }
    } catch {
      // ignore legacy error
    }
    return '';
  },
  openExternal: (url: string) => ipcRenderer.invoke('shell:open_external', url),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  resizeWindow: (width: number, height: number) => ipcRenderer.invoke('window:resize', { width, height }),
  setTrayState: (state: 'idle' | 'ingesting' | 'alert' | 'error') => ipcRenderer.invoke('tray:set_state', state),
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
  onNoteCreated: (callback: (note: any) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, noteData: any) => callback(noteData);
    ipcRenderer.on('daemon:note_created', handler);
    return () => {
      ipcRenderer.removeListener('daemon:note_created', handler);
    };
  },

  testMascotEmotion: (emotion: string | null) => {
    ipcRenderer.send('dev:test_mascot_emotion', emotion);
  },
  cycleAllEmotions: async () => {
    const emotions = ['welcome', 'idle', 'hover_drop', 'ingesting', 'ready', 'alert', 'error'];
    console.log('%c[Ekko Test Bench] Début du cycle des 7 micro-émotions de la mascotte...', 'color: #38bdf8; font-weight: bold;');
    for (const em of emotions) {
      console.log(`%c[Ekko Test Bench] Emotion en test : %c${em}%c (2.5s)`, 'color: #94a3b8;', 'color: #22c55e; font-weight: bold;', 'color: #94a3b8;');
      ipcRenderer.send('dev:test_mascot_emotion', em);
      await new Promise((res) => setTimeout(res, 2500));
    }
    console.log('%c[Ekko Test Bench] Fin du cycle. Retour au mode nominal automatique.', 'color: #38bdf8; font-weight: bold;');
    ipcRenderer.send('dev:test_mascot_emotion', null);
  },
  onTestMascotEmotion: (callback: (emotion: string | null) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, emotion: string | null) => callback(emotion);
    ipcRenderer.on('dev:set_mascot_emotion', handler);
    return () => {
      ipcRenderer.removeListener('dev:set_mascot_emotion', handler);
    };
  },
};

contextBridge.exposeInMainWorld('ekkoAPI', api);

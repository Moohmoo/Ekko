export interface NoteItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  tags: string[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ekko';
  content: string;
  timestamp: string;
}

export type PodTab = 'home' | 'chat' | 'echo';
export type ViewMode = 'welcome' | 'home' | 'chat' | 'echo' | 'settings';

export interface PingResult {
  status: string;
  timestamp: string;
}

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
  ping: () => Promise<PingResult | null>;
  getNotes: () => Promise<unknown[]>;
  getPendingSignals: () => Promise<SignalsResult | Signal[]>;
  resolveSignal: (signalId: string, action: 'archive' | 'discard') => Promise<{ status: string; signal_id?: string; action?: string }>;
  resolveAllPendingSignals: (action: 'archive' | 'discard') => Promise<{ status: string; action?: string; count?: number }>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<IngestResult>;
  ingestUrl: (url: string) => Promise<IngestResult>;
  getDroppedFilePath: (file: File) => string;
  closeWindow: () => Promise<void>;
  resizeWindow: (width: number, height: number) => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

declare global {
  interface Window {
    ekkoAPI?: EkkoAPI;
  }
}

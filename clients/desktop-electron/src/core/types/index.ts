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

export interface EkkoAPI {
  ping: () => Promise<PingResult | null>;
  getNotes: () => Promise<unknown[]>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<{ status: string; filename?: string; message?: string; note?: { id: string; title: string; slug: string; summary: string; source?: string } }>;
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

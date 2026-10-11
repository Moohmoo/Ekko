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

export interface PingResult {
  status: string;
  timestamp: string;
}

export interface EkkoAPI {
  ping: () => Promise<PingResult>;
  getNotes: () => Promise<unknown[]>;
  submitPrompt: (prompt: string) => Promise<string>;
  ingestFile: (filePath: string) => Promise<string>;
  closeWindow: () => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

declare global {
  interface Window {
    ekkoAPI?: EkkoAPI;
  }
}

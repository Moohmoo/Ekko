export type MascotState =
  | 'idle'
  | 'ingestion'
  | 'investigation'
  | 'alert'
  | 'drawer'
  | 'dizzy';

export type PodTab = 'home' | 'chat' | 'echo' | 'settings';
export type TabType = PodTab;

export type BYOMProfile = 'micro' | 'standard' | 'large';

export interface DistilledNote {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  source: string;
  sourceType: 'arxiv' | 'url' | 'drop' | 'rss';
  createdAt: string;
  obsidianSaved: boolean;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ekko';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface DaemonStatus {
  connected: boolean;
  niceness: string;
  vramUsageMb: number;
  socketPath: string;
  activeSources: number;
}

export interface NoteItem {
  id: string;
  title: string;
  summary: string;
  content?: string;
  source: string;
  sources?: string[];
  tags: string[];
  created_at?: string;
  score?: number;
}

export interface ToolCallStep {
  id: string;
  tool: string;
  input?: Record<string, unknown>;
  output?: string;
  status: 'running' | 'completed' | 'error';
  duration_ms?: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: number;
  status: 'pending' | 'streaming' | 'complete' | 'error';
  toolCalls?: ToolCallStep[];
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

export interface SearchNotesParams {
  query: string;
  mode?: 'hybrid' | 'lexical' | 'semantic';
  limit?: number;
}

export interface UserContextConfig {
  user_name?: string | null;
  preferred_language: 'fr' | 'en' | string;
  preferences: string[];
  custom_instructions?: string | null;
}

export interface SourceItem {
  id: string;
  type: string;
  url?: string | null;
  path?: string | null;
  interval?: string;
  max_items?: number;
  params?: Record<string, unknown>;
  headers?: Record<string, string>;
  json_items_path?: string | null;
  field_mapping?: Record<string, string>;
  enabled?: boolean;
}

export interface SystemMetadata {
  llm_provider: string;
  active_model: string;
  sqlite_db_path: string;
  ipc_socket_path: string;
  status: string;
}

export interface SystemSettings {
  status?: string;
  user_context: UserContextConfig;
  sources: { sources: SourceItem[] };
  system: SystemMetadata;
}

export interface EkkoAPI {
  ping: () => Promise<PingResult | null>;
  getNotes: () => Promise<unknown[]>;
  searchNotes: (query: string, options?: { mode?: 'hybrid' | 'lexical' | 'semantic'; limit?: number }) => Promise<unknown[]>;
  getPendingSignals: () => Promise<SignalsResult | Signal[]>;
  resolveSignal: (signalId: string, action: 'archive' | 'discard') => Promise<{ status: string; signal_id?: string; action?: string }>;
  resolveAllPendingSignals: (action: 'archive' | 'discard') => Promise<{ status: string; action?: string; count?: number }>;
  submitPrompt: (prompt: string, sessionId?: string) => Promise<string>;
  getSystemSettings: () => Promise<SystemSettings>;
  updateUserContext: (context: Partial<UserContextConfig>) => Promise<{ status: string; user_context: UserContextConfig }>;
  updateSources: (sources: SourceItem[]) => Promise<{ status: string; sources: { sources: SourceItem[] } }>;
  ingestFile: (filePath: string) => Promise<IngestResult>;
  ingestUrl: (url: string) => Promise<IngestResult>;
  getDroppedFilePath: (file: File) => string;
  openExternal: (url: string) => Promise<void>;
  closeWindow: () => Promise<void>;
  resizeWindow: (width: number, height: number) => Promise<void>;
  onPromptChunk: (callback: (chunk: string) => void) => () => void;
  onToolEvent: (callback: (event: any) => void) => () => void;
}

declare global {
  interface Window {
    ekkoAPI?: EkkoAPI;
  }
}

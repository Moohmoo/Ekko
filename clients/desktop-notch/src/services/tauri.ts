/**
 * Tauri v2 IPC communication service with fallback for browser development.
 */

const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

export async function setNotchExpanded(expanded: boolean): Promise<void> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('set_notch_expanded', { expanded });
    } catch (e) {
      console.warn('[Tauri] Failed to set notch expansion:', e);
    }
  }
}

export async function setNotchSize(width: number, height: number): Promise<void> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('set_notch_size', { width, height });
    } catch (e) {
      console.warn('[Tauri] Failed to set notch size:', e);
    }
  }
}

export async function pingDaemon(): Promise<{ status: string; timestamp?: string }> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const res = await invoke<{ status: string; timestamp?: string }>('ping');
      return res;
    } catch (e) {
      console.warn('[Tauri] Ping failed:', e);
      return { status: 'error' };
    }
  }
  return { status: 'ok', timestamp: new Date().toISOString() };
}

export async function scanInbox(limit = 10): Promise<unknown> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke('scan_inbox', { limit });
    } catch (e) {
      console.warn('[Tauri] Scan inbox failed:', e);
    }
  }
  return { signals: [] };
}

export async function queryKnowledge(query: string, mode = 'hybrid', limit = 5): Promise<unknown> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke('query_knowledge', { query, mode, limit });
    } catch (e) {
      console.warn('[Tauri] Query knowledge failed:', e);
    }
  }
  return { results: [] };
}

export async function submitPrompt(prompt: string, sessionId?: string): Promise<void> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('submit_prompt', { prompt, sessionId });
    } catch (e) {
      console.warn('[Tauri] Submit prompt failed:', e);
    }
  }
}

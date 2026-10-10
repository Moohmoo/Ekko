/**
 * Tauri v2 IPC communication service for System Tray Popover Pod.
 */

const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

export async function hideWindow(): Promise<void> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('hide_window');
    } catch (e) {
      console.warn('[Tauri] Failed to hide window:', e);
    }
  }
}

export async function toggleWindow(): Promise<void> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('toggle_window');
    } catch (e) {
      console.warn('[Tauri] Failed to toggle window:', e);
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

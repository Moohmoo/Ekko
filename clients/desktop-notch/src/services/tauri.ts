/**
 * Tauri v2 IPC communication service connecting to local Python Daemon socket.
 */

import type { DistilledNote } from '../types';

const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

export async function checkDaemonStatus(): Promise<boolean> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<boolean>('check_daemon_status');
    } catch (e) {
      console.warn('[IPC] check_daemon_status failed:', e);
      return false;
    }
  }
  return false;
}

export async function submitPromptToDaemon(
  prompt: string,
  sessionId?: string
): Promise<string> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    return await invoke<string>('submit_prompt_to_daemon', { prompt, sessionId });
  }
  throw new Error('Daemon hors ligne. Lancez `uv run ekko daemon`.');
}

export async function getDaemonNotes(limit = 20): Promise<DistilledNote[]> {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const rawSignals = await invoke<Array<Record<string, unknown>>>('get_daemon_notes', {
        limit,
      });

      return rawSignals.map((sig, idx) => {
        const id = String(sig.id || `signal-${idx}`);
        const title = String(sig.title || 'Signal capturé');
        const content = String(sig.content || '');
        const summary = content.length > 160 ? content.slice(0, 160) + '...' : content || 'Signal brut sans contenu.';
        const source = String(sig.source_id || 'Flux');
        const createdAt = sig.created_at ? new Date(String(sig.created_at)).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Récent';

        return {
          id,
          title,
          summary,
          tags: ['signal', source.toLowerCase()],
          source,
          sourceType: 'rss',
          createdAt,
          obsidianSaved: sig.status === 'processed',
        };
      });
    } catch (e) {
      console.warn('[IPC] get_daemon_notes failed:', e);
      return [];
    }
  }
  return [];
}

export async function ingestFilePath(path: string): Promise<unknown> {
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    return await invoke('ingest_file_path', { path });
  }
  throw new Error('Daemon hors ligne. Lancez `uv run ekko daemon`.');
}

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

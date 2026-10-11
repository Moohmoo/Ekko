import { create } from 'zustand';
import type { NoteItem } from '../types';

interface EchoState {
  notes: NoteItem[];
  latestNote: NoteItem | null;
  isLoading: boolean;
  fetchNotes: () => Promise<void>;
}

export const useEchoStore = create<EchoState>((set) => ({
  notes: [],
  latestNote: null,
  isLoading: false,

  fetchNotes: async () => {
    if (!window.ekkoAPI) return;
    set({ isLoading: true });
    try {
      const raw = await window.ekkoAPI.getNotes();
      const mapped: NoteItem[] = (raw as Record<string, unknown>[]).map((item) => ({
        id: String(item.id || ''),
        title: String(item.title || 'Signal brut'),
        summary: String(item.clean_content || ''),
        source: String(item.source_id || 'ekko'),
        tags: [String(item.source_id || 'inbox')],
      }));
      set({
        notes: mapped,
        latestNote: mapped.length > 0 ? mapped[0] : null,
        isLoading: false,
      });
    } catch (e) {
      console.warn('[EchoStore] Erreur récupération notes:', e);
      set({ isLoading: false });
    }
  },
}));

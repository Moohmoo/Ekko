import { create } from 'zustand';
import type { NoteItem } from '../types';

interface EchoState {
  notes: NoteItem[];
  latestNote: NoteItem | null;
  isLoading: boolean;
  fetchNotes: () => Promise<void>;
  setLatestNote: (note: NoteItem) => void;
}

export const useEchoStore = create<EchoState>((set) => ({
  notes: [],
  latestNote: null,
  isLoading: false,

  setLatestNote: (note: NoteItem) => {
    set((state) => ({
      latestNote: note,
      notes: [note, ...state.notes.filter((n) => n.id !== note.id)],
    }));
  },

  fetchNotes: async () => {
    if (!window.ekkoAPI) return;
    set({ isLoading: true });
    try {
      const raw = await window.ekkoAPI.getNotes();
      const mapped: NoteItem[] = (raw as Record<string, unknown>[]).map((item) => ({
        id: String(item.id || item.slug || ''),
        title: String(item.title || 'Signal brut'),
        summary: String(item.summary || item.clean_content || ''),
        source: String(
          (Array.isArray(item.sources) && item.sources[0]) ||
          item.source_id ||
          'ekko'
        ),
        tags: Array.isArray(item.tags)
          ? (item.tags as string[])
          : [String(item.source_id || 'inbox')],
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

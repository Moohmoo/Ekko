import { create } from 'zustand';
import type { NoteItem } from '../types';

export type EchoViewMode = 'browse' | 'search' | 'tag';

interface EchoState {
  notes: NoteItem[];
  latestNote: NoteItem | null;
  isLoading: boolean;
  isOffline: boolean;
  searchQuery: string;
  selectedTag: string | null;
  viewMode: EchoViewMode;
  searchSeq: number;

  // Actions
  fetchNotes: () => Promise<void>;
  searchNotes: (query: string) => Promise<void>;
  filterByTag: (tag: string | null) => void;
  refresh: () => Promise<void>;
  setLatestNote: (note: NoteItem) => void;
}

function mapRawNote(item: Record<string, unknown>): NoteItem {
  // Support both direct note format and wrapped { note: {...}, score: ... }
  const noteData = (item && typeof item === 'object' && item.note && typeof item.note === 'object')
    ? (item.note as Record<string, unknown>)
    : item;

  const score = typeof item.score === 'number' ? item.score : undefined;
  const sources = Array.isArray(noteData.sources)
    ? (noteData.sources as string[])
    : noteData.source
    ? [String(noteData.source)]
    : [];

  const rawTags = Array.isArray(noteData.tags) ? (noteData.tags as string[]) : [];
  const tags = rawTags.length > 0 ? rawTags : [String(noteData.source_id || 'pkm')];

  return {
    id: String(noteData.id || noteData.slug || ''),
    title: String(noteData.title || 'Signal brut'),
    summary: String(noteData.summary || noteData.clean_content || ''),
    content: typeof noteData.content === 'string' ? noteData.content : undefined,
    source: String(sources[0] || noteData.source_id || 'ekko'),
    sources,
    tags,
    created_at: typeof noteData.created_at === 'string' ? noteData.created_at : undefined,
    score,
  };
}

export const useEchoStore = create<EchoState>((set, get) => ({
  notes: [],
  latestNote: null,
  isLoading: false,
  isOffline: false,
  searchQuery: '',
  selectedTag: null,
  viewMode: 'browse',
  searchSeq: 0,

  setLatestNote: (note: NoteItem) => {
    set((state) => ({
      latestNote: note,
      notes: [note, ...state.notes.filter((n) => n.id !== note.id)],
    }));
  },

  filterByTag: (tag: string | null) => {
    set((state) => ({
      selectedTag: tag,
      viewMode: tag ? 'tag' : state.searchQuery.trim() ? 'search' : 'browse',
    }));
  },

  fetchNotes: async () => {
    if (!window.ekkoAPI) return;

    // Strict heartbeat isolation: DO NOT overwrite active search results with browse notes
    if (get().viewMode === 'search') {
      return;
    }

    set({ isLoading: true });
    try {
      const raw = await window.ekkoAPI.getNotes();
      if (Array.isArray(raw)) {
        const mapped: NoteItem[] = (raw as Record<string, unknown>[]).map(mapRawNote);
        set({
          notes: mapped,
          latestNote: mapped.length > 0 ? mapped[0] : null,
          isLoading: false,
          isOffline: false,
          viewMode: get().selectedTag ? 'tag' : 'browse',
        });
      } else {
        // Non-array response (unexpected IPC reply) -> retain existing cache
        set({ isLoading: false, isOffline: true });
      }
    } catch (e) {
      console.warn('[EchoStore] Erreur récupération notes (conservation du cache):', e);
      // Resilience contract: NEVER wipe existing notes on network/socket disconnect
      set({ isLoading: false, isOffline: true });
    }
  },

  searchNotes: async (query: string) => {
    const trimmed = query.trim();

    // Sequence tracking for IPC race condition elimination
    const currentSeq = get().searchSeq + 1;
    set({
      searchQuery: query,
      searchSeq: currentSeq,
      viewMode: trimmed ? 'search' : get().selectedTag ? 'tag' : 'browse',
    });

    if (!trimmed) {
      // Revert to full list of recent notes
      await get().fetchNotes();
      return;
    }

    if (!window.ekkoAPI?.searchNotes) {
      return;
    }

    set({ isLoading: true });
    try {
      const raw = await window.ekkoAPI.searchNotes(trimmed, { mode: 'hybrid', limit: 30 });

      // Discard stale responses if a newer keystroke has already fired
      if (get().searchSeq !== currentSeq) {
        return;
      }

      if (Array.isArray(raw)) {
        const mapped = (raw as Record<string, unknown>[]).map(mapRawNote);
        set({
          notes: mapped,
          isLoading: false,
          isOffline: false,
        });
      } else {
        set({ isLoading: false });
      }
    } catch (e) {
      if (get().searchSeq !== currentSeq) return;
      console.warn('[EchoStore] Erreur recherche hybride:', e);
      set({ isLoading: false, isOffline: true });
    }
  },

  refresh: async () => {
    const { searchQuery, viewMode } = get();
    if (viewMode === 'search' && searchQuery.trim()) {
      await get().searchNotes(searchQuery);
    } else {
      await get().fetchNotes();
    }
  },
}));

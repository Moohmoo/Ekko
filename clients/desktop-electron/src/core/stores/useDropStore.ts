import { create } from 'zustand';
import type { MascotEmotion } from '../../components/Mascot';
import type { NoteItem } from '../types';
import { useBufferStore } from './useBufferStore';
import { RESET_ERROR_DELAY_MS } from '../../design-system/tokens';
import { playDropBlip, playSuccessChime, playErrorThud } from '../audio/soundManager';

export type DropStatus = 'idle' | 'hover' | 'processing' | 'ready' | 'error';

interface DropState {
  dropStatus: DropStatus;
  fileName: string | null;
  mascotEmotion: MascotEmotion;
  forcedEmotion: MascotEmotion | null;
  statusMessage: string;
  errorMessage: string | null;
  pendingFilePath: string | null;
  baselineNoteId: string | null;
  baselineNotesCount: number;

  setHover: (isHovering: boolean) => void;
  setError: (msg: string) => void;
  ingestFileInPlace: (filePath: string) => Promise<boolean>;
  ingestUrlInPlace: (url: string) => Promise<boolean>;
  onDistillationComplete: (note: NoteItem) => void;
  forceMascotEmotion: (emotion: MascotEmotion | null) => void;
  reset: () => void;
}

const SUPPORTED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt'];

export const useDropStore = create<DropState>((set, get) => ({
  dropStatus: 'idle',
  fileName: null,
  mascotEmotion: 'idle',
  forcedEmotion: null,
  statusMessage: 'Tampon actif',
  errorMessage: null,
  pendingFilePath: null,
  baselineNoteId: null,
  baselineNotesCount: 0,

  forceMascotEmotion: (emotion: MascotEmotion | null) => {
    set({ forcedEmotion: emotion });
  },

  setHover: (isHovering: boolean) => {
    if (get().dropStatus === 'processing') return;

    if (isHovering) {
      set({
        dropStatus: 'hover',
        mascotEmotion: 'hover_drop',
        statusMessage: 'Déposer le fichier...',
        errorMessage: null,
      });
    } else {
      if (get().dropStatus === 'hover') {
        set({
          dropStatus: 'idle',
          mascotEmotion: 'idle',
          statusMessage: 'Tampon actif',
          errorMessage: null,
        });
      }
    }
  },

  setError: (msg: string) => {
    playErrorThud();
    set({
      dropStatus: 'error',
      mascotEmotion: 'error',
      statusMessage: 'Format non supporté',
      errorMessage: msg,
    });
    setTimeout(() => {
      if (get().dropStatus === 'error') {
        set({
          dropStatus: 'idle',
          mascotEmotion: 'idle',
          statusMessage: 'Tampon actif',
          errorMessage: null,
        });
      }
    }, RESET_ERROR_DELAY_MS);
  },

  ingestFileInPlace: async (filePath: string) => {
    const fileName = filePath.split('/').pop() || filePath;
    const lower = fileName.toLowerCase();
    const isSupported = SUPPORTED_EXTENSIONS.some((ext) => lower.endsWith(ext));

    if (!isSupported) {
      get().setError('Format non supporté · PDF, Markdown ou TXT uniquement');
      return false;
    }

    const baselineNoteId = useBufferStore.getState().latestNote?.id ?? null;
    const baselineNotesCount = useBufferStore.getState().notes.length;

    playDropBlip();
    set({
      dropStatus: 'processing',
      fileName,
      mascotEmotion: 'ingesting',
      statusMessage: `Distillation de ${fileName} en arrière-plan...`,
      errorMessage: null,
      pendingFilePath: filePath,
      baselineNoteId,
      baselineNotesCount,
    });

    try {
      if (!window.ekkoAPI?.ingestFile) {
        throw new Error('IPC non disponible');
      }

      const res = await window.ekkoAPI.ingestFile(filePath);

      // Handle guardrails responses
      if (res && res.status === 'already_exists') {
        get().setError('Document already indexed in vault');
        return false;
      }

      if (res && res.status === 'rejected') {
        const msg = res.reason === 'file_too_large' ? 'File too large · 25 MB max' : (res.message || 'File rejected');
        get().setError(msg);
        return false;
      }

      // If backend returned completed note synchronously (test/mock fallback)
      if (res && typeof res === 'object' && res.note) {
        const completedNote: NoteItem = {
          id: res.note.id || res.note.slug || String(Date.now()),
          title: res.note.title,
          summary: res.note.summary || '',
          source: res.note.source || fileName,
          tags: ['ingested'],
        };
        useBufferStore.getState().setLatestNote(completedNote);
        get().onDistillationComplete(completedNote);
        return true;
      }

      // Drop & Forget contract: request accepted by daemon (<50ms).
      // Distillation pipeline runs asynchronously in background.
      // Zero mock timers! State remains in 'processing' until useEchoStore
      // detects the persisted note in SQLite.
      return true;
    } catch (err: unknown) {
      console.error('[DropStore:Error] Full ingestion error:', err);
      const rawMsg = (err as Error).message || '';
      let userMsg = 'Error assimilating document';

      if (rawMsg.includes('Fichier introuvable') || rawMsg.includes('ENOENT') || rawMsg.includes('File not found')) {
        userMsg = 'File not found on disk';
      } else if (rawMsg.includes('Fichier illisible') || rawMsg.includes('Permission') || rawMsg.includes('EACCES') || rawMsg.includes('unreadable')) {
        userMsg = 'File unreadable on disk';
      } else if (rawMsg.includes('Format non supporté') || rawMsg.includes('unsupported format')) {
        userMsg = 'Unsupported format · PDF, MD, or TXT only';
      } else if (rawMsg.includes('aucun texte extractible') || rawMsg.includes('no extractable text')) {
        userMsg = 'No extractable text in this document';
      } else if (rawMsg.includes('ECONNREFUSED') || rawMsg.includes('Liaison') || rawMsg.includes('offline')) {
        userMsg = 'Ekko daemon offline';
      }

      playErrorThud();
      set({
        dropStatus: 'error',
        fileName: null,
        mascotEmotion: 'error',
        statusMessage: 'Assimilation error',
        errorMessage: userMsg,
        pendingFilePath: null,
        baselineNoteId: null,
        baselineNotesCount: 0,
      });

      setTimeout(() => {
        if (get().dropStatus === 'error') {
          set({
            dropStatus: 'idle',
            mascotEmotion: 'idle',
            statusMessage: 'Buffer active',
            errorMessage: null,
          });
        }
      }, RESET_ERROR_DELAY_MS);

      return false;
    }
  },

  ingestUrlInPlace: async (url: string) => {
    const trimmed = url.trim();
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      get().setError('Unsupported format · http:// or https:// URL only');
      return false;
    }

    let host = 'web link';
    try {
      const parsed = new URL(trimmed);
      host = parsed.hostname || 'web link';
    } catch {
      // ignore
    }

    const baselineNoteId = useBufferStore.getState().latestNote?.id ?? null;
    const baselineNotesCount = useBufferStore.getState().notes.length;

    playDropBlip();
    set({
      dropStatus: 'processing',
      fileName: host,
      mascotEmotion: 'ingesting',
      statusMessage: `Distilling ${host} in background...`,
      errorMessage: null,
      pendingFilePath: trimmed,
      baselineNoteId,
      baselineNotesCount,
    });

    try {
      if (!window.ekkoAPI?.ingestUrl) {
        throw new Error('IPC unavailable');
      }

      const res = await window.ekkoAPI.ingestUrl(trimmed);

      // Handle guardrails responses
      if (res && res.status === 'already_exists') {
        get().setError('Web link already indexed in vault');
        return false;
      }

      // If backend returned completed note synchronously (test/mock fallback)
      if (res && typeof res === 'object' && res.note) {
        const completedNote: NoteItem = {
          id: res.note.id || res.note.slug || String(Date.now()),
          title: res.note.title,
          summary: res.note.summary || '',
          source: res.note.source || trimmed,
          tags: ['web'],
        };
        useBufferStore.getState().setLatestNote(completedNote);
        get().onDistillationComplete(completedNote);
        return true;
      }

      // Drop & Forget: request accepted by daemon (<50ms).
      return true;
    } catch (err: unknown) {
      console.error('[DropStore:Error] Full URL ingestion error:', err);
      const rawMsg = (err as Error).message || '';
      let userMsg = 'Error assimilating web link';

      if (rawMsg.includes('Format') || rawMsg.includes('invalide') || rawMsg.includes('invalid')) {
        userMsg = 'Invalid URL format';
      } else if (rawMsg.includes('SSRF') || rawMsg.includes('Security')) {
        userMsg = 'URL access denied (network security)';
      } else if (rawMsg.includes('ECONNREFUSED') || rawMsg.includes('Liaison') || rawMsg.includes('offline')) {
        userMsg = 'Ekko daemon offline';
      }

      playErrorThud();
      set({
        dropStatus: 'error',
        fileName: null,
        mascotEmotion: 'error',
        statusMessage: 'Assimilation error',
        errorMessage: userMsg,
        pendingFilePath: null,
        baselineNoteId: null,
        baselineNotesCount: 0,
      });

      setTimeout(() => {
        if (get().dropStatus === 'error') {
          set({
            dropStatus: 'idle',
            mascotEmotion: 'idle',
            statusMessage: 'Buffer active',
            errorMessage: null,
          });
        }
      }, RESET_ERROR_DELAY_MS);

      return false;
    }
  },

  onDistillationComplete: (_note: NoteItem) => {
    playSuccessChime();
    set({
      dropStatus: 'ready',
      mascotEmotion: 'ready',
      statusMessage: 'Document absorbed into cognitive buffer ✓',
      pendingFilePath: null,
      baselineNoteId: null,
      baselineNotesCount: 0,
    });

    // Brief visual confirmation before returning dropzone to idle
    setTimeout(() => {
      if (get().dropStatus === 'ready') {
        set({
          dropStatus: 'idle',
          fileName: null,
          mascotEmotion: 'idle',
          statusMessage: 'Buffer active',
        });
      }
    }, 2000);
  },

  reset: () => {
    set({
      dropStatus: 'idle',
      fileName: null,
      mascotEmotion: 'idle',
      statusMessage: 'Buffer active',
      errorMessage: null,
      pendingFilePath: null,
      baselineNoteId: null,
      baselineNotesCount: 0,
      forcedEmotion: null,
    });
  },
}));

// Reactive subscription: when SQLite updates via scan_notes in useBufferStore,
// complete pending ingestion if a new note is detected.
useBufferStore.subscribe((bufferState) => {
  const dropState = useDropStore.getState();
  if (dropState.dropStatus !== 'processing') return;

  const newLatest = bufferState.latestNote;
  if (!newLatest) return;

  const isNew =
    newLatest.id !== dropState.baselineNoteId ||
    bufferState.notes.length > dropState.baselineNotesCount;

  const matchesPending = dropState.pendingFilePath
    ? newLatest.source === dropState.pendingFilePath ||
      newLatest.source.includes(dropState.fileName || '')
    : false;

  if (isNew || matchesPending) {
    dropState.onDistillationComplete(newLatest);
  }
});

// Push IPC listener: instant reactive trigger at t=0ms when daemon completes note persistence
if (typeof window !== 'undefined' && window.ekkoAPI?.onNoteCreated) {
  window.ekkoAPI.onNoteCreated((data) => {
    // 1. Immediate background fetch to refresh Buffer store without waiting for heartbeat
    useBufferStore.getState().fetchNotes({ silent: true });

    // 2. Complete pending drop instantly at t=0ms
    const dropState = useDropStore.getState();
    if (dropState.dropStatus === 'processing') {
      const completedNote: NoteItem = {
        id: data.note_id || data.slug || String(Date.now()),
        title: data.title,
        summary: data.summary || '',
        source: data.source || dropState.fileName || 'ekko',
        tags: ['ingested'],
      };
      useBufferStore.getState().setLatestNote(completedNote);
      dropState.onDistillationComplete(completedNote);
    }
  });
}

// Dev test bench listener: allows external control of mascot emotions
if (typeof window !== 'undefined' && window.ekkoAPI?.onTestMascotEmotion) {
  window.ekkoAPI.onTestMascotEmotion((emotion) => {
    useDropStore.getState().forceMascotEmotion(emotion as MascotEmotion | null);
  });
}

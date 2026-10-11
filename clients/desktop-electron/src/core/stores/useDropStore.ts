import { create } from 'zustand';
import type { MascotEmotion } from '../../components/Mascot';
import type { NoteItem } from '../types';
import { useEchoStore } from './useEchoStore';
import { RESET_ERROR_DELAY_MS } from '../../design-system/tokens';
import { playDropBlip, playSuccessChime, playErrorThud } from '../audio/soundManager';

export type DropStatus = 'idle' | 'hover' | 'processing' | 'ready' | 'error';

interface DropState {
  dropStatus: DropStatus;
  fileName: string | null;
  mascotEmotion: MascotEmotion;
  statusMessage: string;
  errorMessage: string | null;
  pendingFilePath: string | null;
  baselineNoteId: string | null;
  baselineNotesCount: number;

  setHover: (isHovering: boolean) => void;
  setError: (msg: string) => void;
  ingestFileInPlace: (filePath: string) => Promise<boolean>;
  onDistillationComplete: (note: NoteItem) => void;
  reset: () => void;
}

const SUPPORTED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt'];

export const useDropStore = create<DropState>((set, get) => ({
  dropStatus: 'idle',
  fileName: null,
  mascotEmotion: 'idle',
  statusMessage: 'Tampon actif',
  errorMessage: null,
  pendingFilePath: null,
  baselineNoteId: null,
  baselineNotesCount: 0,

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

    const baselineNoteId = useEchoStore.getState().latestNote?.id ?? null;
    const baselineNotesCount = useEchoStore.getState().notes.length;

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

      // If backend returned completed note synchronously (test/mock fallback)
      if (res && typeof res === 'object' && res.note) {
        const completedNote: NoteItem = {
          id: res.note.id || res.note.slug || String(Date.now()),
          title: res.note.title,
          summary: res.note.summary || '',
          source: res.note.source || fileName,
          tags: ['ingested'],
        };
        useEchoStore.getState().setLatestNote(completedNote);
        get().onDistillationComplete(completedNote);
        return true;
      }

      // Drop & Forget contract: request accepted by daemon (<50ms).
      // Distillation pipeline runs asynchronously in background.
      // Zero mock timers! State remains in 'processing' until useEchoStore
      // detects the persisted note in SQLite.
      return true;
    } catch (err: unknown) {
      console.error('[DropStore:Error] Erreur complète ingestion:', err);
      const rawMsg = (err as Error).message || '';
      let userMsg = "Erreur lors de l'assimilation du document";

      if (rawMsg.includes('Fichier introuvable') || rawMsg.includes('ENOENT')) {
        userMsg = 'Fichier introuvable sur le disque';
      } else if (rawMsg.includes('Fichier illisible') || rawMsg.includes('Permission') || rawMsg.includes('EACCES')) {
        userMsg = 'Fichier illisible sur le disque';
      } else if (rawMsg.includes('Format non supporté')) {
        userMsg = 'Format non supporté · PDF, MD ou TXT uniquement';
      } else if (rawMsg.includes('aucun texte extractible')) {
        userMsg = 'Aucun texte extractible dans ce document';
      } else if (rawMsg.includes('ECONNREFUSED') || rawMsg.includes('Liaison')) {
        userMsg = 'Daemon Ekko hors ligne';
      }

      playErrorThud();
      set({
        dropStatus: 'error',
        fileName: null,
        mascotEmotion: 'error',
        statusMessage: 'Erreur assimilation',
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
            statusMessage: 'Tampon actif',
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
      statusMessage: 'Document absorbé dans le tampon cognitif ✓',
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
          statusMessage: 'Tampon actif',
        });
      }
    }, 2000);
  },

  reset: () => {
    set({
      dropStatus: 'idle',
      fileName: null,
      mascotEmotion: 'idle',
      statusMessage: 'Tampon actif',
      errorMessage: null,
      pendingFilePath: null,
      baselineNoteId: null,
      baselineNotesCount: 0,
    });
  },
}));

// Reactive subscription: when SQLite updates via scan_notes in useEchoStore,
// complete pending ingestion if a new note is detected.
useEchoStore.subscribe((echoState) => {
  const dropState = useDropStore.getState();
  if (dropState.dropStatus !== 'processing') return;

  const newLatest = echoState.latestNote;
  if (!newLatest) return;

  const isNew =
    newLatest.id !== dropState.baselineNoteId ||
    echoState.notes.length > dropState.baselineNotesCount;

  const matchesPending = dropState.pendingFilePath
    ? newLatest.source === dropState.pendingFilePath ||
      newLatest.source.includes(dropState.fileName || '')
    : false;

  if (isNew || matchesPending) {
    dropState.onDistillationComplete(newLatest);
  }
});

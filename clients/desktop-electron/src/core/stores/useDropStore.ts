import { create } from 'zustand';
import type { MascotEmotion } from '../../components/Mascot';
import { useEchoStore } from './useEchoStore';

export type DropStatus = 'idle' | 'hover' | 'distilling' | 'success' | 'error';

interface DropState {
  dropStatus: DropStatus;
  fileName: string | null;
  mascotEmotion: MascotEmotion;
  statusMessage: string;
  errorMessage: string | null;

  setHover: (isHovering: boolean) => void;
  setError: (msg: string) => void;
  ingestFileInPlace: (filePath: string) => Promise<boolean>;
  reset: () => void;
}

const SUPPORTED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt'];

export const useDropStore = create<DropState>((set, get) => ({
  dropStatus: 'idle',
  fileName: null,
  mascotEmotion: 'idle',
  statusMessage: 'Tampon actif',
  errorMessage: null,

  setHover: (isHovering: boolean) => {
    if (get().dropStatus === 'distilling') return;

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
    set({
      dropStatus: 'error',
      mascotEmotion: 'idle',
      statusMessage: 'Format non supporté',
      errorMessage: msg,
    });
    setTimeout(() => {
      set({
        dropStatus: 'idle',
        statusMessage: 'Tampon actif',
        errorMessage: null,
      });
    }, 3000);
  },

  ingestFileInPlace: async (filePath: string) => {
    const fileName = filePath.split('/').pop() || filePath;
    const lower = fileName.toLowerCase();
    const isSupported = SUPPORTED_EXTENSIONS.some((ext) => lower.endsWith(ext));

    if (!isSupported) {
      get().setError('Format non supporté · PDF, Markdown ou TXT uniquement');
      return false;
    }

    set({
      dropStatus: 'distilling',
      fileName,
      mascotEmotion: 'ingesting',
      statusMessage: 'Distillation en cours...',
      errorMessage: null,
    });

    try {
      if (!window.ekkoAPI?.ingestFile) {
        throw new Error('IPC non disponible');
      }

      const res = (await window.ekkoAPI.ingestFile(filePath)) as {
        status?: string;
        note?: { id?: string; slug?: string; title: string; summary?: string; source?: string };
      };

      // If backend returned a note object, update echo store immediately
      if (res && typeof res === 'object' && res.note) {
        useEchoStore.getState().setLatestNote({
          id: res.note.id || res.note.slug || String(Date.now()),
          title: res.note.title,
          summary: res.note.summary || '',
          source: res.note.source || fileName,
          tags: ['ingested'],
        });
      } else {
        await useEchoStore.getState().fetchNotes();
      }

      set({
        dropStatus: 'success',
        mascotEmotion: 'ready',
        statusMessage: 'Document assimilé et indexé ✓',
      });

      // Keep success state for 2 seconds before returning to idle
      setTimeout(() => {
        set({
          dropStatus: 'idle',
          fileName: null,
          mascotEmotion: 'idle',
          statusMessage: 'Tampon actif',
        });
      }, 2000);

      return true;
    } catch (err: unknown) {
      const errMsg = (err as Error).message || 'Erreur lors de la distillation';
      console.warn('[DropStore] Erreur ingestion:', err);
      set({
        dropStatus: 'error',
        fileName: null,
        mascotEmotion: 'idle',
        statusMessage: 'Erreur distillation',
        errorMessage: errMsg,
      });

      setTimeout(() => {
        set({
          dropStatus: 'idle',
          statusMessage: 'Tampon actif',
          errorMessage: null,
        });
      }, 3000);

      return false;
    }
  },

  reset: () => {
    set({
      dropStatus: 'idle',
      fileName: null,
      mascotEmotion: 'idle',
      statusMessage: 'Tampon actif',
      errorMessage: null,
    });
  },
}));

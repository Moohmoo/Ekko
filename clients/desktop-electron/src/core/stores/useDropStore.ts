import { create } from 'zustand';
import type { MascotEmotion } from '../../components/Mascot';

export type DropStatus = 'idle' | 'hover' | 'uploading' | 'distilling' | 'success';

interface DropState {
  dropStatus: DropStatus;
  progress: number;
  fileName: string | null;
  mascotEmotion: MascotEmotion;
  statusMessage: string;

  setHover: (isHovering: boolean) => void;
  ingestFileInPlace: (filePath: string) => Promise<void>;
  reset: () => void;
}

export const useDropStore = create<DropState>((set, get) => ({
  dropStatus: 'idle',
  progress: 0,
  fileName: null,
  mascotEmotion: 'idle',
  statusMessage: 'Tampon actif',

  setHover: (isHovering: boolean) => {
    if (get().dropStatus === 'uploading' || get().dropStatus === 'distilling') return;

    if (isHovering) {
      set({
        dropStatus: 'hover',
        mascotEmotion: 'hover_drop',
        statusMessage: 'Déposer le fichier...',
      });
    } else {
      set({
        dropStatus: 'idle',
        mascotEmotion: 'idle',
        statusMessage: 'Tampon actif',
      });
    }
  },

  ingestFileInPlace: async (filePath: string) => {
    const fileName = filePath.split('/').pop() || filePath;
    set({
      dropStatus: 'uploading',
      progress: 25,
      fileName,
      mascotEmotion: 'ingesting',
      statusMessage: 'Absorption...',
    });

    // Simulate fast local ingestion progression for visual feedback
    const progressInterval = setInterval(() => {
      const current = get().progress;
      if (current < 85) {
        set({ progress: current + 20 });
      }
    }, 150);

    try {
      if (window.ekkoAPI?.ingestFile) {
        set({ dropStatus: 'distilling', statusMessage: 'Distillation locale...' });
        await window.ekkoAPI.ingestFile(filePath);
      }
      clearInterval(progressInterval);

      set({
        dropStatus: 'success',
        progress: 100,
        mascotEmotion: 'ready',
        statusMessage: 'Indexé avec succès !',
      });

      // After 1.5s, return to idle
      setTimeout(() => {
        set({
          dropStatus: 'idle',
          progress: 0,
          fileName: null,
          mascotEmotion: 'idle',
          statusMessage: 'Tampon actif',
        });
      }, 1500);
    } catch (err) {
      clearInterval(progressInterval);
      console.warn('[DropStore] Erreur ingestion:', err);
      set({
        dropStatus: 'idle',
        progress: 0,
        fileName: null,
        mascotEmotion: 'idle',
        statusMessage: 'Erreur ingestion',
      });
    }
  },

  reset: () => {
    set({
      dropStatus: 'idle',
      progress: 0,
      fileName: null,
      mascotEmotion: 'idle',
      statusMessage: 'Tampon actif',
    });
  },
}));

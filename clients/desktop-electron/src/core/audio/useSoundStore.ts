import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SoundState {
  isMuted: boolean;
  toggleMute: () => void;
  setMuted: (muted: boolean) => void;
}

export const useSoundStore = create<SoundState>()(
  persist(
    (set) => ({
      isMuted: false,
      toggleMute: () => set((state) => ({ isMuted: !state.isMuted })),
      setMuted: (muted: boolean) => set({ isMuted: muted }),
    }),
    {
      name: 'ekko-sound-settings',
    }
  )
);

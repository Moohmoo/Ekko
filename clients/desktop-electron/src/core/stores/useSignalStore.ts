import { create } from 'zustand';
import type { Signal } from '../../../electron/preload';
import { playSuccessChime, playDropBlip } from '../audio/soundManager';

interface SignalState {
  pendingSignals: Signal[];
  currentSignal: Signal | null;
  isLoading: boolean;

  fetchPendingSignals: () => Promise<void>;
  dismissCurrent: (action: 'archive' | 'discard') => Promise<boolean>;
  setCurrentSignal: (signal: Signal | null) => void;
}

export const useSignalStore = create<SignalState>((set, get) => ({
  pendingSignals: [],
  currentSignal: null,
  isLoading: false,

  fetchPendingSignals: async () => {
    if (!window.ekkoAPI?.getPendingSignals) return;
    try {
      const raw = await window.ekkoAPI.getPendingSignals();
      const signals: Signal[] = Array.isArray(raw) ? raw : [];
      const current = get().currentSignal;

      // Retain current if still present, or pick first pending
      const nextCurrent =
        current && signals.some((s) => s.id === current.id)
          ? current
          : signals.length > 0
          ? signals[0]
          : null;

      set({
        pendingSignals: signals,
        currentSignal: nextCurrent,
      });
    } catch (err) {
      console.error('[SignalStore:ERR] Échec fetchPendingSignals:', err);
    }
  },

  dismissCurrent: async (action: 'archive' | 'discard') => {
    const current = get().currentSignal;
    if (!current || !window.ekkoAPI?.resolveSignal) return false;

    set({ isLoading: true });
    try {
      const res = await window.ekkoAPI.resolveSignal(current.id, action);
      if (res && res.status === 'ok') {
        if (action === 'archive') {
          playSuccessChime();
        } else {
          playDropBlip();
        }

        const remaining = get().pendingSignals.filter((s) => s.id !== current.id);
        set({
          pendingSignals: remaining,
          currentSignal: remaining.length > 0 ? remaining[0] : null,
          isLoading: false,
        });
        return true;
      }
      set({ isLoading: false });
      return false;
    } catch (err) {
      console.error(`[SignalStore:ERR] Échec resolveSignal (${action}):`, err);
      set({ isLoading: false });
      return false;
    }
  },

  setCurrentSignal: (signal: Signal | null) => {
    set({ currentSignal: signal });
  },
}));

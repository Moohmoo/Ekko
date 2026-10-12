import { create } from 'zustand';
import type { Signal } from '../../../electron/preload';
import { playSuccessChime, playDropBlip } from '../audio/soundManager';

export const MAX_PENDING_SIGNALS = 50;

function areSignalIdsEqual(a: Signal[], b: Signal[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].id !== b[i].id) return false;
  }
  return true;
}

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
      const rawSignals: Signal[] = Array.isArray(raw) ? raw : [];
      // Bound the buffer to prevent memory leakage
      const boundedSignals = rawSignals.slice(0, MAX_PENDING_SIGNALS);

      const prevSignals = get().pendingSignals;
      const current = get().currentSignal;

      // Shallow check on signal IDs to avoid spurious re-renders every heartbeat
      if (areSignalIdsEqual(prevSignals, boundedSignals)) {
        return;
      }

      // Retain current if still present, or pick first pending
      const nextCurrent =
        current && boundedSignals.some((s) => s.id === current.id)
          ? current
          : boundedSignals.length > 0
          ? boundedSignals[0]
          : null;

      set({
        pendingSignals: boundedSignals,
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

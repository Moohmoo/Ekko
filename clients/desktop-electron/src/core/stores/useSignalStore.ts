import { create } from 'zustand';
import type { Signal, SignalsResult } from '../types';
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
  totalCount: number;
  currentSignal: Signal | null;
  isLoading: boolean;
  isResolving: boolean;

  fetchPendingSignals: () => Promise<void>;
  dismissCurrent: (action: 'archive' | 'discard') => Promise<boolean>;
  resolveAll: (action: 'archive' | 'discard') => Promise<boolean>;
  setCurrentSignal: (signal: Signal | null) => void;
}

export const useSignalStore = create<SignalState>((set, get) => ({
  pendingSignals: [],
  totalCount: 0,
  currentSignal: null,
  isLoading: false,
  isResolving: false,

  fetchPendingSignals: async () => {
    if (!window.ekkoAPI?.getPendingSignals) return;
    try {
      const raw = await window.ekkoAPI.getPendingSignals();
      let rawSignals: Signal[] = [];
      let reportedTotal = 0;

      if (Array.isArray(raw)) {
        rawSignals = raw;
        reportedTotal = raw.length;
      } else if (raw && typeof raw === 'object' && 'signals' in raw) {
        const payload = raw as SignalsResult;
        rawSignals = Array.isArray(payload.signals) ? payload.signals : [];
        reportedTotal = typeof payload.total_count === 'number' ? payload.total_count : rawSignals.length;
      }

      // Bound the buffer to prevent memory leakage
      const boundedSignals = rawSignals.slice(0, MAX_PENDING_SIGNALS);
      const prevSignals = get().pendingSignals;
      const prevTotal = get().totalCount;
      const current = get().currentSignal;

      // Shallow check on signal IDs and total count to avoid spurious re-renders
      if (areSignalIdsEqual(prevSignals, boundedSignals) && prevTotal === reportedTotal) {
        return;
      }

      // Retain current if still present in new batch, or pick first pending
      const nextCurrent =
        current && boundedSignals.some((s) => s.id === current.id)
          ? current
          : boundedSignals.length > 0
          ? boundedSignals[0]
          : null;

      set({
        pendingSignals: boundedSignals,
        totalCount: reportedTotal,
        currentSignal: nextCurrent,
      });
    } catch (err) {
      console.error('[SignalStore:ERR] Échec fetchPendingSignals:', err);
    }
  },

  dismissCurrent: async (action: 'archive' | 'discard') => {
    const current = get().currentSignal;
    if (!current || !window.ekkoAPI?.resolveSignal) return false;

    // Sound feedback immediately
    if (action === 'archive') {
      playSuccessChime();
    } else {
      playDropBlip();
    }

    // Optimistic FIFO shift: pop current immediately from state
    const remaining = get().pendingSignals.filter((s) => s.id !== current.id);
    const nextTotal = Math.max(0, get().totalCount - 1);
    const nextCurrent = remaining.length > 0 ? remaining[0] : null;

    set({
      pendingSignals: remaining,
      totalCount: nextTotal,
      currentSignal: nextCurrent,
      isResolving: true,
    });

    // Background prefetch replenishment if local buffer runs low while database still holds signals
    if (remaining.length <= 3 && nextTotal > remaining.length) {
      get().fetchPendingSignals();
    }

    try {
      const res = await window.ekkoAPI.resolveSignal(current.id, action);
      set({ isResolving: false });
      return Boolean(res && res.status === 'ok');
    } catch (err) {
      console.error(`[SignalStore:ERR] Échec resolveSignal (${action}):`, err);
      set({ isResolving: false });
      return false;
    }
  },

  resolveAll: async (action: 'archive' | 'discard') => {
    if (!window.ekkoAPI?.resolveAllPendingSignals) return false;

    if (action === 'archive') {
      playSuccessChime();
    } else {
      playDropBlip();
    }

    // Optimistically clear store immediately
    set({
      pendingSignals: [],
      totalCount: 0,
      currentSignal: null,
      isResolving: true,
    });

    try {
      const res = await window.ekkoAPI.resolveAllPendingSignals(action);
      set({ isResolving: false });
      return Boolean(res && res.status === 'ok');
    } catch (err) {
      console.error(`[SignalStore:ERR] Échec resolveAll (${action}):`, err);
      set({ isResolving: false });
      return false;
    }
  },

  setCurrentSignal: (signal: Signal | null) => {
    set({ currentSignal: signal });
  },
}));

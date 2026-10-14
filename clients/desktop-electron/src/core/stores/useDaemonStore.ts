import { create } from 'zustand';

interface DaemonState {
  isOnline: boolean;
  lastPingTimestamp: string | null;
  vramUsageMb: number;
  niceness: string;
  isChecking: boolean;
  error: string | null;

  // Actions
  checkHealth: () => Promise<boolean>;
  setOnline: (online: boolean) => void;
}

export const useDaemonStore = create<DaemonState>((set) => ({
  isOnline: false,
  lastPingTimestamp: null,
  vramUsageMb: 0,
  niceness: 'nice +10',
  isChecking: false,
  error: null,

  setOnline: (online: boolean) => set({ isOnline: online }),

  checkHealth: async () => {
    if (!window.ekkoAPI) {
      console.warn('[DaemonStore] window.ekkoAPI is undefined (preload not ready)');
      set({ isOnline: false, error: 'PRELOAD_UNAVAILABLE' });
      return false;
    }

    set({ isChecking: true });
    try {
      const res = await window.ekkoAPI.ping();
      const online = Boolean(res && res.status === 'ok');
      set({
        isOnline: online,
        lastPingTimestamp: res?.timestamp || new Date().toISOString(),
        isChecking: false,
        error: null,
      });
      return online;
    } catch (err: unknown) {
      const msg = (err as Error).message || 'PING_FAILED';
      set({
        isOnline: false,
        isChecking: false,
        error: msg,
      });
      return false;
    }
  },
}));

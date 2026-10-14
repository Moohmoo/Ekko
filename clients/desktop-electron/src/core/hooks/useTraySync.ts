import { useEffect, useRef } from 'react';
import { useSignalStore } from '../stores/useSignalStore';
import { useDropStore } from '../stores/useDropStore';
import { useDaemonStore } from '../stores/useDaemonStore';

export type DynamicTrayState = 'idle' | 'ingesting' | 'alert' | 'error';

/**
 * Hook to automatically synchronize the OS System Tray icon
 * with real application states (Drop, Alerts, Idle).
 */
export function useTraySync(): void {
  const currentSignal = useSignalStore((state) => state.currentSignal);
  const dropStatus = useDropStore((state) => state.dropStatus);
  const isOnline = useDaemonStore((state) => state.isOnline);
  const lastStateRef = useRef<DynamicTrayState | null>(null);

  useEffect(() => {
    if (!window.ekkoAPI?.setTrayState) return;

    let targetState: DynamicTrayState = 'idle';

    if (dropStatus === 'processing') {
      targetState = 'ingesting';
    } else if (dropStatus === 'error') {
      targetState = 'error';
    } else if (currentSignal !== null) {
      targetState = 'alert';
    } else {
      targetState = 'idle';
    }

    if (lastStateRef.current !== targetState) {
      lastStateRef.current = targetState;
      window.ekkoAPI.setTrayState(targetState).catch((err) => {
        console.error('[TraySync:ERR] Failed to update tray state:', err);
      });
    }
  }, [dropStatus, currentSignal, isOnline]);
}

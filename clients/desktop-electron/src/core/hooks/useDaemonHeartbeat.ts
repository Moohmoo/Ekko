import { useEffect } from 'react';
import { useDaemonStore } from '../stores/useDaemonStore';
import { useEchoStore } from '../stores/useEchoStore';
import { useSignalStore } from '../stores/useSignalStore';

const HEARTBEAT_INTERVAL_MS = 2000;

/**
 * Root hook driving the daemon health check lifecycle, periodic note sync, and signal polling.
 * Triggers an immediate ping on mount, then polls every 2 seconds.
 */
export function useDaemonHeartbeat(): void {
  const checkHealth = useDaemonStore((state) => state.checkHealth);

  useEffect(() => {
    // Immediate first check and data retrieval
    checkHealth();
    useEchoStore.getState().fetchNotes();
    useSignalStore.getState().fetchPendingSignals();

    // Heartbeat ticker
    const timer = setInterval(() => {
      checkHealth().then((online) => {
        if (online) {
          useEchoStore.getState().fetchNotes();
          useSignalStore.getState().fetchPendingSignals();
        }
      });
    }, HEARTBEAT_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [checkHealth]);
}

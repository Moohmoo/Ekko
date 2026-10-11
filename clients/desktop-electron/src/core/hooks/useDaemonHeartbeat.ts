import { useEffect } from 'react';
import { useDaemonStore } from '../stores/useDaemonStore';
import { useEchoStore } from '../stores/useEchoStore';

const HEARTBEAT_INTERVAL_MS = 2000;

/**
 * Root hook driving the daemon health check lifecycle and periodic note sync.
 * Triggers an immediate ping on mount, then polls every 2 seconds.
 */
export function useDaemonHeartbeat(): void {
  const checkHealth = useDaemonStore((state) => state.checkHealth);

  useEffect(() => {
    // Immediate first check and note retrieval
    checkHealth();
    useEchoStore.getState().fetchNotes();

    // Heartbeat ticker
    const timer = setInterval(() => {
      checkHealth().then((online) => {
        if (online) {
          useEchoStore.getState().fetchNotes();
        }
      });
    }, HEARTBEAT_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [checkHealth]);
}

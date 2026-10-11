import { useEffect } from 'react';
import { useDaemonStore } from '../stores/useDaemonStore';

const HEARTBEAT_INTERVAL_MS = 2000;

/**
 * Root hook driving the daemon health check lifecycle.
 * Triggers an immediate ping on mount, then polls every 2 seconds.
 */
export function useDaemonHeartbeat(): void {
  const checkHealth = useDaemonStore((state) => state.checkHealth);

  useEffect(() => {
    // Immediate first check
    checkHealth();

    // Heartbeat ticker
    const timer = setInterval(() => {
      checkHealth();
    }, HEARTBEAT_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [checkHealth]);
}

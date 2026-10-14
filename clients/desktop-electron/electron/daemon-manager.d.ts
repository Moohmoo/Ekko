interface DaemonManagerOptions {
    socketPath?: string;
    repoRoot?: string;
    maxWaitMs?: number;
    retryIntervalMs?: number;
}
/**
 * Check if the daemon UNIX socket is actively listening and responsive.
 */
export declare function isSocketAlive(socketPath?: string): Promise<boolean>;
/**
 * Find the repository root containing pyproject.toml.
 */
export declare function findRepoRoot(): string;
/**
 * Ensure the Python daemon is running.
 * If already active, adopts it (no-op).
 * If absent, spawns `uv run ekko daemon` and polls until socket accepts connections.
 */
export declare function ensureDaemonRunning(options?: DaemonManagerOptions): Promise<boolean>;
/**
 * Graceful termination of the managed daemon.
 * Sends SIGTERM, waits, and forces SIGKILL after timeout.
 */
export declare function stopDaemonIfManaged(): Promise<void>;
export {};

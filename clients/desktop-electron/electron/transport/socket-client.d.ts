export declare const DEFAULT_SOCKET_PATH = "/tmp/ekko.sock";
export interface JSONRPCResponse<T = unknown> {
    jsonrpc: '2.0';
    result?: T;
    error?: {
        code: number;
        message: string;
    };
    id?: number | string;
}
/**
 * Send a single JSON-RPC 2.0 request over the UNIX domain socket.
 * Accumulates buffer until newline and logs operations with [IPC:REQ], [IPC:RES], [IPC:ERR].
 */
export declare function sendJsonRpc<T = unknown>(method: string, params?: Record<string, unknown>, socketPath?: string): Promise<T>;
export interface ToolEventPayload {
    type: 'tool_call_started' | 'tool_call_completed';
    tool_call_id: string;
    tool_name: string;
    arguments?: Record<string, unknown>;
    success?: boolean;
    summary?: string;
    duration_ms?: number;
}
/**
 * Stream prompt execution over UNIX domain socket line-by-line (NDJSON EngineEvents).
 */
export declare function streamPrompt(prompt: string, onChunk: (chunk: string) => void, onComplete: (fullText: string) => void, onError: (error: string) => void, onToolEvent?: (event: ToolEventPayload) => void, sessionId?: string, socketPath?: string): void;
/**
 * Long-lived connection listening for server-pushed JSON-RPC notifications (e.g. daemon:note_created).
 * Features automatic silent reconnection with exponential backoff if daemon restarts.
 */
export declare function subscribeDaemonEvents(onEvent: (method: string, params: Record<string, unknown>) => void, socketPath?: string): () => void;

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
/**
 * Stream prompt execution over UNIX domain socket line-by-line (NDJSON EngineEvents).
 */
export declare function streamPrompt(prompt: string, onChunk: (chunk: string) => void, onComplete: (fullText: string) => void, onError: (error: string) => void, socketPath?: string): void;

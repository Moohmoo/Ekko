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
 * Send single request to the Ekko UNIX domain socket and await single response.
 */
export declare function sendJsonRpc<T = unknown>(method: string, params?: Record<string, unknown>, socketPath?: string): Promise<T>;
/**
 * Stream prompt execution over UNIX domain socket, invoking chunk and completion callbacks.
 */
export declare function streamPrompt(prompt: string, onChunk: (chunk: string) => void, onComplete: (fullText: string) => void, onError: (error: string) => void, socketPath?: string): void;

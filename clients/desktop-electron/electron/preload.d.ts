export interface Signal {
    id: string;
    title: string;
    source_type: string;
    source_url: string;
    summary: string;
    created_at: string;
}
export interface EkkoAPI {
    ping: () => Promise<{
        status: string;
        timestamp: string;
    } | null>;
    getNotes: () => Promise<unknown[]>;
    getPendingSignals: () => Promise<Signal[]>;
    resolveSignal: (signalId: string, action: 'archive' | 'discard') => Promise<{
        status: string;
        signal_id?: string;
        action?: string;
    }>;
    submitPrompt: (prompt: string) => Promise<string>;
    ingestFile: (filePath: string) => Promise<{
        status: string;
        filename?: string;
        message?: string;
        note?: {
            id: string;
            title: string;
            slug: string;
            summary: string;
            source?: string;
        };
    }>;
    getDroppedFilePath: (file: File) => string;
    closeWindow: () => Promise<void>;
    resizeWindow: (width: number, height: number) => Promise<void>;
    onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

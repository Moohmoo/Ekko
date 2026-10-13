export interface Signal {
    id: string;
    title: string;
    source_type: string;
    source_url: string;
    summary: string;
    created_at: string;
}
export interface SignalsResult {
    signals: Signal[];
    total_count: number;
}
export interface IngestResult {
    status: string;
    filename?: string;
    url?: string;
    message?: string;
    reason?: string;
    content_hash?: string;
    max_bytes?: number;
    note?: {
        id: string;
        title: string;
        slug: string;
        summary: string;
        source?: string;
    };
}
export interface EkkoAPI {
    ping: () => Promise<{
        status: string;
        timestamp: string;
    } | null>;
    getNotes: () => Promise<unknown[]>;
    searchNotes: (query: string, options?: {
        mode?: 'hybrid' | 'lexical' | 'semantic';
        limit?: number;
    }) => Promise<unknown[]>;
    getPendingSignals: () => Promise<SignalsResult | Signal[]>;
    resolveSignal: (signalId: string, action: 'archive' | 'discard') => Promise<{
        status: string;
        signal_id?: string;
        action?: string;
    }>;
    resolveAllPendingSignals: (action: 'archive' | 'discard') => Promise<{
        status: string;
        action?: string;
        count?: number;
    }>;
    submitPrompt: (prompt: string, sessionId?: string) => Promise<string>;
    getSystemSettings: () => Promise<unknown>;
    updateUserContext: (context: unknown) => Promise<unknown>;
    updateSources: (sources: unknown[]) => Promise<unknown>;
    ingestFile: (filePath: string) => Promise<IngestResult>;
    ingestUrl: (url: string) => Promise<IngestResult>;
    getDroppedFilePath: (file: File) => string;
    openExternal: (url: string) => Promise<void>;
    closeWindow: () => Promise<void>;
    resizeWindow: (width: number, height: number) => Promise<void>;
    onPromptChunk: (callback: (chunk: string) => void) => () => void;
    onToolEvent: (callback: (event: any) => void) => () => void;
}

export interface EkkoAPI {
    ping: () => Promise<{
        status: string;
        timestamp: string;
    } | null>;
    getNotes: () => Promise<unknown[]>;
    submitPrompt: (prompt: string) => Promise<string>;
    ingestFile: (filePath: string) => Promise<string>;
    closeWindow: () => Promise<void>;
    onPromptChunk: (callback: (chunk: string) => void) => () => void;
}

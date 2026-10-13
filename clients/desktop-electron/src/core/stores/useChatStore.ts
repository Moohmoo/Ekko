import { create } from 'zustand';
import type { ChatMessage, ToolCallStep } from '../types';

interface ChatState {
  sessionId: string;
  messages: ChatMessage[];
  isStreaming: boolean;
  errorMessage: string | null;

  // Actions
  submitPrompt: (prompt: string) => Promise<void>;
  appendChunk: (chunk: string) => void;
  updateToolCall: (step: ToolCallStep) => void;
  completeTurn: (finalContent?: string) => void;
  clearSession: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: `desktop-${Date.now()}`,
  messages: [],
  isStreaming: false,
  errorMessage: null,

  submitPrompt: async (prompt: string) => {
    const trimmed = prompt.trim();
    if (!trimmed || get().isStreaming || !window.ekkoAPI) return;

    const userMsgId = `msg-${Date.now()}`;
    const asstMsgId = `asst-${Date.now() + 1}`;
    const now = Date.now();

    const userMessage: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      content: trimmed,
      timestamp: now,
      status: 'complete',
    };

    const assistantMessage: ChatMessage = {
      id: asstMsgId,
      sender: 'assistant',
      content: '',
      timestamp: now + 1,
      status: 'streaming',
      toolCalls: [],
    };

    set((state) => ({
      messages: [...state.messages, userMessage, assistantMessage],
      isStreaming: true,
      errorMessage: null,
    }));

    // Attach IPC chunk / token listeners
    const cleanupChunk = window.ekkoAPI.onPromptChunk
      ? window.ekkoAPI.onPromptChunk((chunk) => {
          get().appendChunk(chunk);
        })
      : () => {};

    const cleanupChatToken = window.ekkoAPI.onChatToken
      ? window.ekkoAPI.onChatToken((token) => {
          get().appendChunk(token);
        })
      : () => {};

    const cleanupChatDone = window.ekkoAPI.onChatDone
      ? window.ekkoAPI.onChatDone(() => {
          get().completeTurn();
        })
      : () => {};

    // Attach IPC tool event listener
    const cleanupTool = window.ekkoAPI.onToolEvent
      ? window.ekkoAPI.onToolEvent((event) => {
          if (!event) return;
          const step: ToolCallStep = {
            id: String(event.tool_call_id || Date.now()),
            tool: String(event.tool_name || 'outil'),
            input: (event.arguments as Record<string, unknown>) || undefined,
            output: event.summary,
            status: event.type === 'tool_call_completed' ? (event.success === false ? 'error' : 'completed') : 'running',
            duration_ms: typeof event.duration_ms === 'number' ? event.duration_ms : undefined,
          };
          get().updateToolCall(step);
        })
      : () => {};

    const cleanupAll = () => {
      cleanupChunk();
      cleanupChatToken();
      cleanupChatDone();
      cleanupTool();
    };

    try {
      let fullResponse: string;
      if (window.ekkoAPI.sendChatMessage) {
        fullResponse = await window.ekkoAPI.sendChatMessage(trimmed, get().messages);
      } else {
        fullResponse = await window.ekkoAPI.submitPrompt(trimmed, get().sessionId);
      }
      cleanupAll();
      get().completeTurn(fullResponse);
    } catch (err: unknown) {
      cleanupAll();
      const message = (err as Error)?.message || 'Erreur lors de la réponse.';
      set((state) => {
        const msgs = [...state.messages];
        const lastIdx = msgs.findIndex((m) => m.id === asstMsgId);
        if (lastIdx !== -1) {
          msgs[lastIdx] = {
            ...msgs[lastIdx],
            status: 'error',
            content: msgs[lastIdx].content || message,
          };
        }
        return {
          messages: msgs,
          isStreaming: false,
          errorMessage: message,
        };
      });
    }
  },

  appendChunk: (chunk: string) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.sender === 'assistant' && last.status === 'streaming') {
        msgs[msgs.length - 1] = {
          ...last,
          content: last.content + chunk,
        };
        return { messages: msgs };
      }
      return state;
    });
  },

  updateToolCall: (step: ToolCallStep) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.sender === 'assistant') {
        const currentTools = last.toolCalls ? [...last.toolCalls] : [];
        const existingIdx = currentTools.findIndex((t) => t.id === step.id);
        if (existingIdx !== -1) {
          currentTools[existingIdx] = {
            ...currentTools[existingIdx],
            ...step,
          };
        } else {
          currentTools.push(step);
        }
        msgs[msgs.length - 1] = {
          ...last,
          toolCalls: currentTools,
        };
        return { messages: msgs };
      }
      return state;
    });
  },

  completeTurn: (finalContent?: string) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.sender === 'assistant') {
        msgs[msgs.length - 1] = {
          ...last,
          content: finalContent !== undefined ? finalContent : last.content,
          status: 'complete',
        };
        return {
          messages: msgs,
          isStreaming: false,
        };
      }
      return { isStreaming: false };
    });
  },

  clearSession: () => {
    set({
      sessionId: `desktop-${Date.now()}`,
      messages: [],
      isStreaming: false,
      errorMessage: null,
    });
  },
}));

import React, { useState } from 'react';
import type { ChatMessage } from '../../core/types';
import { useDaemonStore } from '../../core/stores/useDaemonStore';
import { Send, AlertCircle } from 'lucide-react';

interface ChatViewProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => Promise<void>;
  isStreaming: boolean;
  errorMessage: string | null;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  onSendMessage,
  isStreaming,
  errorMessage,
}) => {
  const isOnline = useDaemonStore((state) => state.isOnline);
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput('');
    onSendMessage(trimmed);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-3.5 gap-2.5">
      {/* Offline / Error Banner derived from Zustand */}
      {(!isOnline || errorMessage) && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-950/40 border border-red-500/30 text-red-200 text-xs">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <span className="truncate">
            {errorMessage || 'Daemon hors ligne. Lancez `uv run ekko daemon`.'}
          </span>
        </div>
      )}

      {/* Message List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 text-xs">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-slate-500 text-center px-4">
            Posez une question ou demandez une synthèse sur vos fiches PKM.
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 leading-relaxed break-words ${
                msg.sender === 'user'
                  ? 'bg-sky-600 text-white border border-sky-400/30'
                  : 'bg-white/[0.04] text-slate-100 border border-white/5'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              <div
                className={`text-[9px] mt-1 text-right ${
                  msg.sender === 'user' ? 'text-sky-200/70' : 'text-slate-400'
                }`}
              >
                {msg.timestamp}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input Bar */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/10 focus-within:border-sky-400/40 transition-colors"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Demander à Ekko..."
          disabled={!isOnline || isStreaming}
          className="flex-1 bg-transparent border-none outline-none text-xs text-slate-100 placeholder:text-slate-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || isStreaming || !isOnline}
          className="w-7 h-7 rounded-full bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:opacity-40 flex items-center justify-center text-slate-900 transition-colors shrink-0"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};

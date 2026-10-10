import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import type { ChatMessage } from '../../types';

interface AssistantTabProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isStreaming: boolean;
}

export const AssistantTab: React.FC<AssistantTabProps> = ({
  messages,
  onSendMessage,
  isStreaming,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleQuickPrompt = (prompt: string) => {
    if (isStreaming) return;
    onSendMessage(prompt);
  };

  return (
    <div className="flex flex-col h-[340px] justify-between">
      {/* Messages Thread */}
      <div className="space-y-3 overflow-y-auto pr-1 flex-1 mb-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-2 ${
              msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] ${
                msg.sender === 'user'
                  ? 'bg-slate-700 text-slate-200'
                  : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              }`}
            >
              {msg.sender === 'user' ? (
                <User className="w-3.5 h-3.5" />
              ) : (
                <Bot className="w-3.5 h-3.5" />
              )}
            </div>

            <div
              className={`p-2.5 rounded-xl text-xs leading-relaxed max-w-[85%] ${
                msg.sender === 'user'
                  ? 'bg-cyan-950/60 border border-cyan-800/40 text-cyan-100'
                  : 'bg-slate-900/90 border border-white/5 text-slate-300 shadow-sm'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              <div className="text-[9px] text-slate-500 mt-1 font-mono text-right">
                {msg.timestamp}
              </div>
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex items-center gap-2 text-xs text-cyan-400 bg-slate-900/50 p-2 rounded-xl border border-white/5">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span className="font-mono text-[10.5px]">Ekko consulte le PKM...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick suggestions if few messages */}
      {messages.length <= 1 && (
        <div className="flex items-center gap-1.5 mb-2 overflow-x-auto pb-1 text-[10px]">
          <button
            onClick={() => handleQuickPrompt('Quelles sont les dernières ruptures IA ?')}
            className="whitespace-nowrap px-2 py-1 rounded-lg bg-white/5 hover:bg-cyan-950/40 hover:text-cyan-300 text-slate-400 border border-white/5 transition-colors"
          >
            ⚡ Dernières ruptures
          </button>
          <button
            onClick={() => handleQuickPrompt('Recherche dans mes notes sur les architectures LLM')}
            className="whitespace-nowrap px-2 py-1 rounded-lg bg-white/5 hover:bg-cyan-950/40 hover:text-cyan-300 text-slate-400 border border-white/5 transition-colors"
          >
            🔍 RAG Architectures
          </button>
        </div>
      )}

      {/* Input Form */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-1.5 pt-2 border-t border-white/5"
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Poser une question à Ekko (RAG FTS5 + vecteurs)..."
          disabled={isStreaming}
          className="flex-1 bg-black/40 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-400/80 transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isStreaming || !inputText.trim()}
          className="p-1.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          title="Envoyer"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};

export default AssistantTab;

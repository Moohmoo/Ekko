import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Loader2, AlertCircle } from 'lucide-react';
import { EkkoMascot } from '../mascot/EkkoMascot';
import type { ChatMessage, BYOMProfile } from '../../types';

interface ChatViewProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isStreaming: boolean;
  currentProfile: BYOMProfile;
  daemonConnected: boolean;
  errorMessage?: string | null;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  onSendMessage,
  isStreaming,
  currentProfile,
  daemonConnected,
  errorMessage,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming, errorMessage]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const getProfileLabel = () => {
    switch (currentProfile) {
      case 'micro':
        return 'Micro 1.5B (Local Qwen)';
      case 'standard':
        return 'Standard 7B (Local Mistral)';
      case 'large':
        return 'Large 32B / API';
    }
  };

  return (
    <div className="flex-1 flex flex-col justify-between p-4 overflow-hidden h-full">
      {/* Top Model Badge */}
      <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.06] text-[10.5px] flex-shrink-0">
        <div className="flex items-center gap-1.5 font-medium text-slate-300">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              daemonConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
            }`}
          />
          <span>{daemonConnected ? getProfileLabel() : 'Daemon déconnecté'}</span>
        </div>
        <span className="font-mono text-[9.5px] text-slate-500">
          /tmp/ekko.sock
        </span>
      </div>

      {/* Messages Scrollable Thread */}
      <div className="flex-1 overflow-y-auto my-3 pr-1 space-y-3 min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-2 ${
              msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            {msg.sender === 'ekko' && (
              <div className="flex-shrink-0 mt-0.5">
                <EkkoMascot state="drawer" size="sm" />
              </div>
            )}

            <div
              className={`p-3 rounded-2xl text-xs leading-relaxed max-w-[85%] ${
                msg.sender === 'user'
                  ? 'bg-cyan-950/60 border border-cyan-800/40 text-cyan-100 rounded-tr-sm'
                  : 'bg-white/[0.05] border border-white/[0.08] text-slate-200 rounded-tl-sm shadow-md'
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
              <div className="text-[9px] text-slate-500 mt-1.5 font-mono text-right">
                {msg.timestamp}
              </div>
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex items-center gap-2 text-xs text-cyan-300 bg-white/[0.04] p-2.5 rounded-2xl border border-white/[0.06] w-fit flex-shrink-0">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400 flex-shrink-0" />
            <span className="font-mono text-[10.5px]">Ekko consulte le PKM...</span>
          </div>
        )}

        {errorMessage && (
          <div className="flex items-center gap-2 text-xs text-rose-300 bg-rose-950/40 p-2.5 rounded-2xl border border-rose-800/40 w-full flex-shrink-0">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span className="font-mono text-[10.5px]">{errorMessage}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Suggestion Pills */}
      {messages.length <= 1 && (
        <div className="flex items-center gap-1.5 mb-2.5 overflow-x-auto pb-1 text-[10px] flex-shrink-0">
          <button
            onClick={() => onSendMessage('Quelles sont les dernières ruptures IA ?')}
            className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white/[0.04] hover:bg-cyan-950/40 hover:text-cyan-300 text-slate-400 border border-white/[0.06] transition-colors cursor-pointer"
          >
            ⚡ Dernières ruptures
          </button>
          <button
            onClick={() => onSendMessage('Synthèse de mes notes sur les architectures LLM')}
            className="whitespace-nowrap px-2.5 py-1 rounded-full bg-white/[0.04] hover:bg-cyan-950/40 hover:text-cyan-300 text-slate-400 border border-white/[0.06] transition-colors cursor-pointer"
          >
            🔍 RAG Architectures
          </button>
        </div>
      )}

      {/* Rounded Bottom Input with Circular Arrow Button */}
      <form onSubmit={handleSubmit} className="relative flex items-center flex-shrink-0">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={daemonConnected ? "Poser une question à Ekko..." : "Daemon déconnecté - lancez `uv run ekko daemon`"}
          disabled={isStreaming}
          className="w-full rounded-full bg-white/[0.05] border border-white/[0.1] pl-4 pr-11 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-400/80 transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isStreaming || !inputText.trim()}
          className="absolute right-1.5 w-7 h-7 rounded-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 flex items-center justify-center transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer shadow-md"
          title="Envoyer"
          aria-label="Envoyer"
        >
          <ArrowUp className="w-3.5 h-3.5 stroke-[2.5]" />
        </button>
      </form>
    </div>
  );
};

export default ChatView;

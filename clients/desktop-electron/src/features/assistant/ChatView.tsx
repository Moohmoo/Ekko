import React, { useState, useRef, useEffect } from 'react';
import { useDaemonStore } from '../../core/stores/useDaemonStore';
import { useChatStore } from '../../core/stores/useChatStore';
import { MarkdownRenderer } from '../echo/MarkdownRenderer';
import { Send, AlertCircle, Trash2, Loader2, CheckCircle2, ChevronRight, ChevronDown, Sparkles } from 'lucide-react';
import type { ToolCallStep } from '../../core/types';

function formatToolTitle(tool: string): string {
  switch (tool) {
    case 'query_knowledge':
      return 'Recherche dans le coffre';
    case 'get_recent_notes':
      return 'Consultation des derniers échos';
    case 'read_resource':
      return 'Lecture de ressource';
    case 'save_note':
      return 'Enregistrement de note';
    case 'scan_inbox':
      return 'Consultation des signaux';
    case 'system_info':
      return 'Diagnostic système';
    default:
      return `Outil : ${tool}`;
  }
}

interface ToolBadgeProps {
  toolCall: ToolCallStep;
}

const ToolBadge: React.FC<ToolBadgeProps> = ({ toolCall }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isRunning = toolCall.status === 'running';
  const isError = toolCall.status === 'error';

  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] overflow-hidden text-[11px] my-1 transition-colors">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-2.5 py-1.5 hover:bg-white/[0.04] text-slate-300 transition-colors gap-2 text-left"
      >
        <div className="flex items-center gap-1.5 min-w-0">
          {isRunning ? (
            <Loader2 className="w-3 h-3 text-sky-400 animate-spin shrink-0" />
          ) : isError ? (
            <AlertCircle className="w-3 h-3 text-rose-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
          )}
          <span className="font-medium text-slate-200 truncate">
            {formatToolTitle(toolCall.tool)}
          </span>
        </div>
        <div className="text-slate-400 shrink-0">
          {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-2 border-t border-white/[0.04] bg-black/20 text-[10px] font-mono text-slate-400 space-y-1">
          {toolCall.input && Object.keys(toolCall.input).length > 0 && (
            <div>
              <span className="text-slate-400 uppercase font-sans text-[9px] font-semibold">Paramètres:</span>
              <pre className="whitespace-pre-wrap text-slate-300 mt-0.5 max-h-24 overflow-y-auto">
                {JSON.stringify(toolCall.input, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.output && (
            <div>
              <span className="text-slate-400 uppercase font-sans text-[9px] font-semibold">Résultat:</span>
              <pre className="whitespace-pre-wrap text-emerald-300/90 mt-0.5 max-h-24 overflow-y-auto">
                {toolCall.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const ChatView: React.FC = () => {
  const isOnline = useDaemonStore((state) => state.isOnline);
  const messages = useChatStore((state) => state.messages);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const errorMessage = useChatStore((state) => state.errorMessage);
  const submitPrompt = useChatStore((state) => state.submitPrompt);
  const clearSession = useChatStore((state) => state.clearSession);

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll when messages or streaming content update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Adjust textarea height up to 4 lines dynamically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      // Cap at ~100px (approx 4-5 lines)
      textareaRef.current.style.height = `${Math.min(scrollHeight, 100)}px`;
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !isOnline) return;
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    submitPrompt(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-3 gap-2 select-none relative">
      {/* Top Bar with Clear Action and Offline Warning */}
      <div className="flex items-center justify-between shrink-0 px-1">
        <div className="flex items-center gap-1.5 text-xs text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-medium tracking-tight">✦ Copilote</span>
        </div>
        {messages.length > 0 && (
          <button
            onClick={() => clearSession()}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-rose-400 px-2 py-1 rounded-lg hover:bg-white/[0.04] transition-colors"
            title="Nouvelle conversation"
          >
            <Trash2 className="w-3 h-3" />
            <span>Nouveau dialogue</span>
          </button>
        )}
      </div>

      {/* Offline / Standby Status Banner */}
      {!isOnline && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/[0.06] border border-amber-500/20 text-amber-200/90 text-[11px] shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400/80 animate-pulse shrink-0" />
          <span className="truncate">Assistant en veille</span>
        </div>
      )}

      {/* Error Banner */}
      {errorMessage && isOnline && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 text-xs shrink-0">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <span className="truncate">{errorMessage}</span>
        </div>
      )}

      {/* Message List */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs select-text">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 text-center px-6 gap-2 select-none">
            <div className="w-10 h-10 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center text-sky-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <p className="font-medium text-slate-300">Comment puis-je vous aider ?</p>
            <p className="text-[11px] text-slate-400 max-w-sm">
              Posez une question, explorez vos fiches de connaissances ou parcourez les dernières veilles.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 leading-relaxed break-words ${
                msg.sender === 'user'
                  ? 'bg-white/[0.08] text-slate-100 border border-white/[0.08] rounded-tr-sm shadow-sm'
                  : 'bg-white/[0.03] text-slate-100 border border-white/[0.06] rounded-tl-sm shadow-sm w-full'
              }`}
            >
              {/* Tool calls badges above assistant content */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mb-2 space-y-1">
                  {msg.toolCalls.map((tc) => (
                    <ToolBadge key={tc.id} toolCall={tc} />
                  ))}
                </div>
              )}

              {/* Message content */}
              {msg.sender === 'user' ? (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              ) : (
                <div>
                  {msg.content ? (
                    <MarkdownRenderer content={msg.content} />
                  ) : msg.status === 'streaming' ? (
                    <div className="flex items-center gap-1.5 text-slate-400 py-1 text-xs italic">
                      <Loader2 className="w-3 h-3 animate-spin text-sky-400" />
                      <span>Réflexion en cours...</span>
                    </div>
                  ) : null}
                </div>
              )}

              {/* Message Timestamp & Status */}
              <div
                className={`text-[9px] mt-1.5 flex items-center gap-1.5 ${
                  msg.sender === 'user' ? 'justify-end text-slate-400' : 'justify-start text-slate-400'
                }`}
              >
                <span>
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {msg.status === 'streaming' && (
                  <span className="text-sky-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
                    <span>génération...</span>
                  </span>
                )}
                {msg.status === 'error' && (
                  <span className="text-rose-400 font-medium">Échec</span>
                )}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar with Multi-line Textarea */}
      <div className="shrink-0 flex items-end gap-2 px-3 py-1.5 rounded-2xl bg-white/[0.04] border border-white/[0.08] focus-within:border-sky-500/40 focus-within:bg-white/[0.06] transition-colors">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Poser une question à Ekko... (Maj+Entrée pour saut de ligne)"
          disabled={!isOnline || isStreaming}
          className="flex-1 bg-transparent border-none outline-none text-xs text-slate-100 placeholder:text-slate-500 resize-none max-h-24 py-1 leading-relaxed disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={!input.trim() || isStreaming || !isOnline}
          className="w-7 h-7 rounded-xl bg-white/[0.08] hover:bg-sky-500 hover:text-slate-950 border border-white/[0.08] text-slate-300 disabled:opacity-30 disabled:pointer-events-none flex items-center justify-center transition-all shrink-0 mb-0.5"
          title="Envoyer (Entrée)"
        >
          {isStreaming ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Check, Copy, FileText, Sparkles, RefreshCw } from 'lucide-react';
import type { DistilledNote } from '../../types';

interface EchoViewProps {
  notes: DistilledNote[];
  onCopyNote: (note: DistilledNote) => void;
  onRefreshNotes?: () => void;
  isLoading?: boolean;
}

export const EchoView: React.FC<EchoViewProps> = ({
  notes,
  onCopyNote,
  onRefreshNotes,
  isLoading = false,
}) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (note: DistilledNote) => {
    onCopyNote(note);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col p-4 overflow-hidden h-full">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.06] text-[11px] text-slate-400 flex-shrink-0">
        <span className="font-medium flex items-center gap-1.5 text-slate-200">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          Fiches distillées (Daemon PKM)
        </span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9.5px] text-slate-500">
            {notes.length} signal{notes.length > 1 ? 's' : ''}
          </span>
          {onRefreshNotes && (
            <button
              onClick={onRefreshNotes}
              disabled={isLoading}
              className="p-1 rounded-md hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
              title="Rafraîchir les notes"
              aria-label="Rafraîchir les notes"
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable Bento List */}
      <div className="flex-1 overflow-y-auto my-2 pr-1 space-y-2.5 min-h-0">
        {notes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-500 text-xs">
            <FileText className="w-8 h-8 mb-2.5 opacity-25 text-cyan-400" />
            <p className="font-medium text-slate-400">Aucun signal distillé pour l’instant</p>
            <p className="text-[10.5px] text-slate-500 mt-1 max-w-[240px]">
              Déposez un lien ou un document dans l’Accueil pour le faire analyser par Ekko.
            </p>
          </div>
        ) : (
          notes.map((note) => (
            <div
              key={note.id}
              className="p-3 rounded-2xl bg-white/[0.03] border border-white/[0.06] hover:border-cyan-500/30 transition-all duration-200 group shadow-md"
            >
              <div className="flex items-center justify-between text-[10px] mb-1 font-mono">
                <span
                  className={`px-1.5 py-0.5 rounded-md border uppercase tracking-wider text-[9px] ${
                    note.sourceType === 'arxiv'
                      ? 'text-cyan-300 bg-cyan-950/60 border-cyan-800/40'
                      : note.sourceType === 'drop'
                      ? 'text-emerald-300 bg-emerald-950/60 border-emerald-800/40'
                      : 'text-amber-300 bg-amber-950/60 border-amber-800/40'
                  }`}
                >
                  {note.source}
                </span>
                <span className="text-slate-500">{note.createdAt}</span>
              </div>

              <h4 className="text-xs font-semibold text-slate-200 group-hover:text-cyan-200 transition-colors line-clamp-1">
                {note.title}
              </h4>

              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                {note.summary}
              </p>

              <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.05] text-[10px]">
                <div className="flex items-center gap-1.5 text-slate-500 font-mono">
                  {note.tags.map((tag) => (
                    <span key={tag} className="hover:text-cyan-400 transition-colors">
                      #{tag}
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  {note.obsidianSaved && (
                    <span className="text-emerald-400 flex items-center gap-0.5 font-medium text-[9.5px]">
                      <Check className="w-2.5 h-2.5" />
                      Obsidian
                    </span>
                  )}
                  <button
                    onClick={() => handleCopy(note)}
                    className="p-1 px-1.5 rounded-lg bg-white/[0.04] hover:bg-cyan-950/50 hover:text-cyan-300 text-slate-400 transition-colors flex items-center gap-1 font-mono text-[9.5px] cursor-pointer"
                    title="Copier en Markdown"
                  >
                    {copiedId === note.id ? (
                      <>
                        <Check className="w-2.5 h-2.5 text-emerald-400" />
                        <span className="text-emerald-400">Copié</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-2.5 h-2.5" />
                        <span>Markdown</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EchoView;

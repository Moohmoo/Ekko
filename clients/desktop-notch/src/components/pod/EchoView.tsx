import React, { useState } from 'react';
import { Check, Copy, FileText, Sparkles } from 'lucide-react';
import type { DistilledNote } from '../../types';

interface EchoViewProps {
  notes: DistilledNote[];
  onCopyNote: (note: DistilledNote) => void;
}

export const EchoView: React.FC<EchoViewProps> = ({ notes, onCopyNote }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (note: DistilledNote) => {
    onCopyNote(note);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col p-4 overflow-hidden">
      {/* Top Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.06] text-[11px] text-slate-400">
        <span className="font-medium flex items-center gap-1.5 text-slate-200">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          Fiches distillées récentes (PKM)
        </span>
        <span className="font-mono text-[9.5px] text-slate-500">
          {notes.length} fiches synchronisées
        </span>
      </div>

      {/* Scrollable Bento List */}
      <div className="flex-1 overflow-y-auto my-2 pr-1 space-y-2.5">
        {notes.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            <FileText className="w-7 h-7 mx-auto mb-2 opacity-30 text-cyan-400" />
            Aucun signal en attente. Déposez un document dans l’Accueil !
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

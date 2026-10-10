import React, { useState } from 'react';
import { Check, Copy, FileText, Sparkles } from 'lucide-react';
import type { DistilledNote } from '../../types';

interface EchoTabProps {
  notes: DistilledNote[];
  onCopyNote: (note: DistilledNote) => void;
}

export const EchoTab: React.FC<EchoTabProps> = ({ notes, onCopyNote }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (note: DistilledNote) => {
    onCopyNote(note);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
      <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1 px-0.5">
        <span className="font-medium flex items-center gap-1.5 text-slate-300">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          Fiches distillées récentes (PKM)
        </span>
        <span className="font-mono text-[10px] text-slate-500">SQLite-vec · FTS5</span>
      </div>

      {notes.length === 0 ? (
        <div className="p-6 text-center text-slate-500 text-xs">
          <FileText className="w-6 h-6 mx-auto mb-2 opacity-30 text-cyan-400" />
          Aucune fiche en attente. Déposez une ressource dans Drop & Forget !
        </div>
      ) : (
        notes.map((note) => (
          <div
            key={note.id}
            className="p-3 rounded-xl bg-slate-900/80 border border-white/5 hover:border-cyan-500/30 transition-all duration-200 group shadow-md"
          >
            <div className="flex items-center justify-between text-[10px] mb-1 font-mono">
              <span
                className={`px-1.5 py-0.5 rounded border uppercase tracking-wider ${
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

            <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5 text-[10px]">
              <div className="flex items-center gap-1.5 text-slate-500 font-mono">
                {note.tags.map((tag) => (
                  <span key={tag} className="hover:text-cyan-400 transition-colors">
                    #{tag}
                  </span>
                ))}
              </div>

              <div className="flex items-center gap-2">
                {note.obsidianSaved && (
                  <span className="text-emerald-400 flex items-center gap-0.5 font-medium">
                    <Check className="w-2.5 h-2.5" />
                    Obsidian
                  </span>
                )}
                <button
                  onClick={() => handleCopy(note)}
                  className="p-1 px-1.5 rounded bg-white/5 hover:bg-cyan-950/50 hover:text-cyan-300 text-slate-400 transition-colors flex items-center gap-1 font-mono"
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
  );
};

export default EchoTab;

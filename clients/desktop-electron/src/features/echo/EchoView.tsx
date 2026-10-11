import React from 'react';
import type { NoteItem } from '../../core/types';
import { Layers, Copy, Check } from 'lucide-react';

interface EchoViewProps {
  notes: NoteItem[];
  onRefresh: () => void;
  isLoading: boolean;
}

export const EchoView: React.FC<EchoViewProps> = ({ notes, onRefresh, isLoading }) => {
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  const handleCopy = (note: NoteItem) => {
    const md = `# ${note.title}\n\n${note.summary}\n\nSource: ${note.source}\n`;
    navigator.clipboard?.writeText(md);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-3.5 gap-2.5">
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>Fiches distillées ({notes.length})</span>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-[11px] text-sky-400 hover:text-sky-300 disabled:opacity-40"
        >
          {isLoading ? 'Chargement...' : 'Rafraîchir'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
        {notes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2">
            <Layers className="w-8 h-8 opacity-40" />
            <span>Aucune note dans le tampon cognitif.</span>
          </div>
        ) : (
          notes.map((note) => (
            <div
              key={note.id}
              className="p-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/10 transition-colors flex flex-col gap-1.5"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-slate-100 text-[11px] line-clamp-1">
                  {note.title}
                </span>
                <button
                  onClick={() => handleCopy(note)}
                  className="p-1 rounded hover:bg-white/5 text-slate-400 hover:text-slate-200 transition-colors shrink-0"
                  title="Copier en Markdown"
                >
                  {copiedId === note.id ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                {note.summary}
              </p>
              <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                <span>{note.source}</span>
                <span className="px-1.5 py-0.5 rounded bg-white/5 text-slate-400">
                  #{note.tags[0] || 'pkm'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

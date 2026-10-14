import React, { useState } from 'react';
import type { NoteItem } from '../../core/types';
import { Copy, Check, ExternalLink, Calendar, Tag, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import { SPRING_SNAPPY } from '../../design-system/tokens';
import { MarkdownRenderer } from './components/MarkdownRenderer';
import { formatSourceDisplay, normalizeTag } from '../../core/utils/formatters';

interface BufferDetailViewProps {
  note: NoteItem;
  onBack: () => void;
  onSelectTag?: (tag: string) => void;
}

/**
 * Full-page reader for a single Buffer note with instant markdown copying,
 * Obsidian link formatting, and external source navigation.
 */
export const BufferDetailView: React.FC<BufferDetailViewProps> = ({
  note,
  onBack,
  onSelectTag,
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  // Keyboard shortcut: Escape to return to notes list
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onBack();
      }
    };
    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [onBack]);

  const handleCopyMarkdown = () => {
    const fullText = note.content || note.summary;
    const md = `# ${note.title}\n\n${fullText}\n\n${
      note.sources && note.sources.length > 0
        ? `Sources:\n${note.sources.map((s) => `- ${s}`).join('\n')}`
        : `Source: ${note.source}`
    }\n`;

    navigator.clipboard?.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenSource = (url: string) => {
    if (window.ekkoAPI?.openExternal) {
      window.ekkoAPI.openExternal(url);
    } else {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return null;
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return null;
    }
  };

  const formattedDate = formatDate(note.created_at);
  const primarySourceRaw = (note.sources && note.sources[0]) || note.source;
  const sourceInfo = formatSourceDisplay(primarySourceRaw);

  return (
    <motion.div
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={SPRING_SNAPPY}
      className="flex-1 flex flex-col h-full w-full min-h-0 select-none overflow-hidden"
    >
      {/* 1. Header bar with seamless in-place back navigation */}
      <div className="flex items-center justify-between pb-2.5 border-b border-white/[0.08] shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-medium text-slate-400 hover:text-sky-300 hover:bg-white/[0.06] transition-colors"
          title="Retour à la liste (Échap)"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Retour</span>
        </button>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleCopyMarkdown}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-white/[0.05] hover:bg-white/10 text-slate-300 hover:text-white transition-colors border border-white/5"
            title="Copier la fiche complète en Markdown"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copié !</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copier MD</span>
              </>
            )}
          </button>

          <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded bg-white/5 font-mono text-[9.5px] text-slate-500 border border-white/5">
            Échap
          </span>
        </div>
      </div>

      {/* 2. Reader Body */}
      <div className="flex-1 overflow-y-auto pr-1 py-3 space-y-3 min-h-0 text-xs">
        {/* Title & Metadata */}
        <div className="space-y-1.5">
          <h2 className="text-base font-semibold text-slate-100 leading-snug">
            {note.title}
          </h2>

          <div className="flex flex-wrap items-center gap-2 pt-0.5 text-[11px] text-slate-400">
            {formattedDate && (
              <div className="flex items-center gap-1 text-slate-400">
                <Calendar className="w-3 h-3 opacity-60" />
                <span>{formattedDate}</span>
              </div>
            )}

            {sourceInfo.isUrl ? (
              <button
                onClick={() => handleOpenSource(sourceInfo.raw)}
                className="flex items-center gap-1 text-sky-400 hover:text-sky-300 hover:underline max-w-[280px] truncate"
                title={sourceInfo.raw}
              >
                <ExternalLink className="w-3 h-3 shrink-0" />
                <span className="truncate">{sourceInfo.label}</span>
              </button>
            ) : (
              <span className="text-slate-400 truncate max-w-[240px]">
                {sourceInfo.label}
              </span>
            )}

            {note.score !== undefined && (
              <span className="px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 text-[10px] font-mono">
                ✦ hybride
              </span>
            )}
          </div>
        </div>

        {/* Tags bar */}
        {note.tags && note.tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
            <Tag className="w-3 h-3 text-slate-500 shrink-0" />
            {note.tags.map((tag) => {
              const norm = normalizeTag(tag);
              return (
                <button
                  key={tag}
                  onClick={() => {
                    if (onSelectTag) {
                      onSelectTag(norm);
                      onBack();
                    }
                  }}
                  className="px-1.5 py-0.5 rounded bg-white/5 hover:bg-sky-500/20 text-slate-400 hover:text-sky-200 transition-colors text-[10px] font-medium"
                  title={`Filtrer par #${norm}`}
                >
                  #{norm}
                </button>
              );
            })}
          </div>
        )}

        {/* Markdown Content */}
        <div className="text-slate-300 text-xs pt-1">
          <MarkdownRenderer content={note.content || note.summary} />
        </div>
      </div>
    </motion.div>
  );
};

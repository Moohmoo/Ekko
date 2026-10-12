import React, { useState } from 'react';
import type { NoteItem } from '../../core/types';
import { X, Copy, Check, ExternalLink, Calendar, Tag, FileText } from 'lucide-react';
import { motion } from 'framer-motion';
import { SPRING_SNAPPY } from '../../design-system/tokens';

interface NoteDetailModalProps {
  note: NoteItem;
  onClose: () => void;
  onSelectTag?: (tag: string) => void;
}

export const NoteDetailModal: React.FC<NoteDetailModalProps> = ({
  note,
  onClose,
  onSelectTag,
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  // Keyboard shortcut: Escape to close
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

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
  const primarySource = (note.sources && note.sources[0]) || note.source;
  const isWebUrl = primarySource && (primarySource.startsWith('http://') || primarySource.startsWith('https://'));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      className="absolute inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.96, opacity: 0, y: 8 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.96, opacity: 0, y: 8 }}
        transition={SPRING_SNAPPY}
        onClick={(e) => e.stopPropagation()}
        className="w-full h-full max-h-[420px] bg-surfaceCard border border-white/10 rounded-2xl flex flex-col overflow-hidden shadow-2xl text-slate-100"
      >
        {/* Header bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.08] bg-white/[0.02] shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="p-1 rounded-md bg-sky-500/10 text-sky-400">
              <FileText className="w-4 h-4" />
            </span>
            <span className="text-[11px] font-medium text-slate-400 truncate">
              Fiche de connaissance PKM
            </span>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
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

            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-colors"
              title="Fermer (Échap)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content body */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3.5 text-xs">
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

              {isWebUrl && (
                <button
                  onClick={() => handleOpenSource(primarySource)}
                  className="flex items-center gap-1 text-sky-400 hover:text-sky-300 hover:underline max-w-[260px] truncate"
                  title={primarySource}
                >
                  <ExternalLink className="w-3 h-3 shrink-0" />
                  <span className="truncate">{primarySource}</span>
                </button>
              )}

              {!isWebUrl && primarySource && (
                <span className="text-slate-500 truncate max-w-[200px]">
                  Source: {primarySource}
                </span>
              )}

              {note.score !== undefined && (
                <span className="px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300 text-[10px] font-mono">
                  Score RRF {(note.score * 100).toFixed(1)}%
                </span>
              )}
            </div>
          </div>

          {/* Tags bar */}
          {note.tags && note.tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              <Tag className="w-3 h-3 text-slate-500 shrink-0" />
              {note.tags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => {
                    if (onSelectTag) {
                      onSelectTag(tag);
                      onClose();
                    }
                  }}
                  className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/[0.05] hover:bg-sky-500/20 text-slate-300 hover:text-sky-200 border border-white/5 transition-colors cursor-pointer"
                  title={`Filtrer par #${tag}`}
                >
                  #{tag}
                </button>
              ))}
            </div>
          )}

          {/* Main Markdown Body */}
          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2 text-slate-300 leading-relaxed font-sans select-text whitespace-pre-wrap">
            {note.content || note.summary}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

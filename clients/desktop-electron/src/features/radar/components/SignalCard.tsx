import React from 'react';
import type { Signal } from '../../../core/types';
import { SURFACES } from '../../../design-system/tokens';
import { Zap, X, Check } from 'lucide-react';

interface SignalCardProps {
  signal: Signal;
  index: number;
  totalCount: number;
  isResolving: boolean;
  onDismiss: () => void;
  onArchive: () => void;
}

function isJsonPayload(text?: string | null): boolean {
  if (!text) return false;
  const trimmed = text.trim();
  return trimmed.startsWith('{') || trimmed.includes('_highlightResult') || trimmed.includes('"objectID"');
}

/**
 * Single Signal card presenting an identified blindspot with triage actions.
 */
export const SignalCard: React.FC<SignalCardProps> = ({
  signal,
  index,
  totalCount,
  isResolving,
  onDismiss,
  onArchive,
}) => {
  const cleanSummary = signal.summary && !isJsonPayload(signal.summary) ? signal.summary : null;

  return (
    <div className={`w-full h-full rounded-xl ${SURFACES.alertCard} flex flex-col justify-between p-3 select-none relative overflow-hidden transition-all shadow-[0_4px_20px_rgba(245,158,11,0.06)] min-h-0`}>
      {/* Header: Amber badge + source + counter */}
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-300">
          <Zap className="w-3 h-3 text-amber-400" />
          <span className="text-[10px] font-semibold tracking-wide uppercase">
            {totalCount > 1 ? `Blindspot ${index + 1} / ${totalCount}` : 'Blindspot detected'}
          </span>
        </div>
        <span className="text-[10px] text-amber-400/80 font-medium truncate max-w-[130px] uppercase tracking-wider">
          {signal.source_type}
        </span>
      </div>

      {/* Content: Title & summary */}
      <div className="flex flex-col gap-1 my-auto min-h-0 overflow-hidden">
        <h3 className="text-xs font-semibold text-white line-clamp-2 leading-tight">
          {signal.title}
        </h3>
        {cleanSummary && (
          <p className="text-[11px] text-zinc-400 line-clamp-3 mt-1 leading-snug">
            {cleanSummary}
          </p>
        )}
      </div>

      {/* Actions: Discard & Archive */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/[0.06] shrink-0">
        <button
          onClick={onDismiss}
          disabled={isResolving}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-colors text-xs font-medium cursor-pointer"
          title="Dismiss signal"
        >
          <X className="w-3.5 h-3.5" />
          <span>Dismiss</span>
        </button>

        <button
          onClick={onArchive}
          disabled={isResolving}
          className="flex items-center gap-1 px-3 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 hover:bg-amber-500/25 transition-all text-xs font-semibold shadow-[0_0_12px_rgba(245,158,11,0.15)] cursor-pointer"
          title="Archive into PKM buffer"
        >
          <Check className="w-3.5 h-3.5 text-amber-400" />
          <span>Archive</span>
        </button>
      </div>
    </div>
  );
};

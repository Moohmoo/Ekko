import React, { useMemo } from 'react';
import type { Signal } from '../../../core/types';
import { SURFACES } from '../../../design-system/tokens';
import { Zap, X, Check, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';

interface SignalCardProps {
  signal: Signal;
  currentIndex: number;
  totalCount: number;
  hasPrev: boolean;
  hasNext: boolean;
  isResolving: boolean;
  onPrev: () => void;
  onNext: () => void;
  onDismiss: () => void;
  onArchive: () => void;
  onDismissAll?: () => void;
  onOpenSource?: () => void;
}

function isJsonPayload(text?: string | null): boolean {
  if (!text) return false;
  const trimmed = text.trim();
  return trimmed.startsWith('{') || trimmed.includes('_highlightResult') || trimmed.includes('"objectID"');
}

/**
 * Single Signal card presenting an identified blindspot with triage actions in compact notch layout.
 */
export const SignalCard: React.FC<SignalCardProps> = ({
  signal,
  currentIndex,
  totalCount,
  hasPrev,
  hasNext,
  isResolving,
  onPrev,
  onNext,
  onDismiss,
  onArchive,
  onDismissAll,
  onOpenSource,
}) => {
  const cleanSummary = signal.summary && !isJsonPayload(signal.summary) ? signal.summary : null;

  const displaySource = useMemo(() => {
    if (signal.source_url) {
      try {
        const url = new URL(signal.source_url);
        return url.hostname.replace(/^www\./, '');
      } catch {
        // Fallback to source_type if URL parsing fails
      }
    }
    return signal.source_type || 'Source';
  }, [signal.source_url, signal.source_type]);

  return (
    <div className={`w-full h-full rounded-xl ${SURFACES.alertCard} flex flex-col justify-between p-2.5 select-none relative overflow-hidden transition-all shadow-[0_4px_20px_rgba(245,158,11,0.06)] min-h-0`}>
      {/* Compact Header: BLINDSPOT 1/10, clickable source, pagination chevrons, Dismiss All */}
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-300 shrink-0">
            <Zap className="w-3 h-3 text-amber-400" />
            <span className="text-[10px] font-semibold tracking-wide uppercase font-mono">
              {totalCount > 1 ? `BLINDSPOT ${currentIndex + 1}/${totalCount}` : 'BLINDSPOT'}
            </span>
          </div>

          <span className="text-white/20 text-[10px]">·</span>

          {signal.source_url ? (
            <button
              type="button"
              onClick={onOpenSource}
              className="inline-flex items-center gap-1 text-[10px] text-amber-400/80 hover:text-amber-300 font-medium truncate max-w-[130px] uppercase tracking-wider transition-colors hover:underline cursor-pointer"
              title={signal.source_url}
            >
              <span className="truncate">{displaySource}</span>
              <ExternalLink className="w-2.5 h-2.5 shrink-0 opacity-70" />
            </button>
          ) : (
            <span className="text-[10px] text-amber-400/80 font-medium truncate max-w-[130px] uppercase tracking-wider">
              {signal.source_type}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {/* Pagination chevrons [ < ] [ > ] */}
          <div className="flex items-center gap-0.5 bg-white/[0.04] border border-white/[0.08] rounded-md p-0.5">
            <button
              type="button"
              onClick={onPrev}
              disabled={!hasPrev || isResolving}
              className="w-4 h-4 flex items-center justify-center rounded text-slate-300 hover:text-white hover:bg-white/[0.08] disabled:opacity-20 disabled:pointer-events-none transition-colors cursor-pointer"
              title="Previous signal"
            >
              <ChevronLeft className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={onNext}
              disabled={!hasNext || isResolving}
              className="w-4 h-4 flex items-center justify-center rounded text-slate-300 hover:text-white hover:bg-white/[0.08] disabled:opacity-20 disabled:pointer-events-none transition-colors cursor-pointer"
              title="Next signal"
            >
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          {/* Dismiss All */}
          {totalCount > 1 && onDismissAll && (
            <button
              type="button"
              onClick={onDismissAll}
              disabled={isResolving}
              className="text-[10px] text-slate-400 hover:text-rose-300 hover:bg-white/[0.04] transition-colors font-medium px-1.5 py-0.5 rounded cursor-pointer"
              title="Dismiss all pending signals"
            >
              Dismiss All
            </button>
          )}
        </div>
      </div>

      {/* Body: Title & summary */}
      <div className="flex-1 flex flex-col justify-center gap-1 min-h-0 overflow-hidden my-auto py-1">
        <h3 className="text-xs font-semibold text-white line-clamp-2 leading-tight">
          {signal.title}
        </h3>
        {cleanSummary && (
          <p className="text-[11px] text-zinc-400 line-clamp-2 leading-snug">
            {cleanSummary}
          </p>
        )}
      </div>

      {/* Footer: Dismiss & Archive */}
      <div className="flex items-center justify-end gap-2 pt-1.5 border-t border-white/[0.06] shrink-0">
        <button
          type="button"
          onClick={onDismiss}
          disabled={isResolving}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-colors text-xs font-medium cursor-pointer"
          title="Dismiss signal"
        >
          <X className="w-3.5 h-3.5" />
          <span>Dismiss</span>
        </button>

        <button
          type="button"
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

export default SignalCard;

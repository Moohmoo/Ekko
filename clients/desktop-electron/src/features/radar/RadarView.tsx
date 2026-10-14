import React, { useEffect } from 'react';
import { useSignalStore } from '../../core/stores/useSignalStore';
import { SignalCard } from './components/SignalCard';
import { Radio, CheckCircle2, RotateCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { SPRING_SNAPPY } from '../../design-system/tokens';

/**
 * RadarView provides a dedicated interface for reviewing distilled intelligence signals,
 * breaking research, and detected blindspots before ingestion into the PKM buffer.
 */
export const RadarView: React.FC = () => {
  const pendingSignals = useSignalStore((state) => state.pendingSignals);
  const totalCount = useSignalStore((state) => state.totalCount);
  const currentSignal = useSignalStore((state) => state.currentSignal);
  const isLoading = useSignalStore((state) => state.isLoading);
  const isResolving = useSignalStore((state) => state.isResolving);
  const fetchPendingSignals = useSignalStore((state) => state.fetchPendingSignals);
  const dismissCurrent = useSignalStore((state) => state.dismissCurrent);
  const resolveAll = useSignalStore((state) => state.resolveAll);

  useEffect(() => {
    fetchPendingSignals();
  }, [fetchPendingSignals]);

  const currentIndex = currentSignal
    ? pendingSignals.findIndex((s) => s.id === currentSignal.id)
    : 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-3 gap-2 select-none relative">
      {/* Top Bar: Title, Count badge, and Bulk actions */}
      <div className="flex items-center justify-between pb-2 border-b border-white/[0.08] shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-lg bg-amber-400/10 text-amber-400">
            <Radio className="w-4 h-4" />
          </div>
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold text-slate-100">
              Radar Watch & Signals
            </h2>
            {totalCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-amber-400/15 border border-amber-400/25 text-amber-300 text-[10px] font-mono font-medium">
                {totalCount}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {totalCount > 10 && (
            <button
              onClick={() => resolveAll('discard')}
              disabled={isResolving}
              className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors font-medium cursor-pointer"
              title="Dismiss all pending signals"
            >
              Dismiss all ({totalCount})
            </button>
          )}

          <button
            onClick={() => fetchPendingSignals()}
            disabled={isLoading}
            className="w-7 h-7 flex items-center justify-center rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-sky-300 disabled:opacity-40 transition-colors"
            title="Refresh signals"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Content Area: Signal Card or Serene Empty State */}
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <AnimatePresence mode="wait">
          {currentSignal ? (
            <motion.div
              key={currentSignal.id}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={SPRING_SNAPPY}
              className="flex-1 h-full min-h-0"
            >
              <SignalCard
                signal={currentSignal}
                index={Math.max(0, currentIndex)}
                totalCount={totalCount}
                isResolving={isResolving}
                onDismiss={() => dismissCurrent('discard')}
                onArchive={() => dismissCurrent('archive')}
              />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex flex-col items-center justify-center gap-2 text-center p-6 rounded-xl bg-white/[0.02] border border-white/[0.06]"
            >
              <CheckCircle2 className="w-8 h-8 text-emerald-400/80 mb-1" />
              <span className="text-xs font-semibold text-slate-200">
                Radar up to date · No blindspots detected
              </span>
              <p className="text-[10px] text-slate-400 max-w-[280px]">
                The daemon scans your sources in the background and will alert you when new signals emerge.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default RadarView;

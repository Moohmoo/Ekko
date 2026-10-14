import React, { useEffect } from 'react';
import { useSignalStore } from '../../core/stores/useSignalStore';
import { SignalCard } from './components/SignalCard';
import { CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { SPRING_SNAPPY } from '../../design-system/tokens';

/**
 * RadarView provides a compact notch interface for reviewing distilled intelligence signals,
 * breaking research, and detected blindspots before ingestion into the PKM buffer.
 */
export const RadarView: React.FC = () => {
  const pendingSignals = useSignalStore((state) => state.pendingSignals);
  const totalCount = useSignalStore((state) => state.totalCount);
  const currentSignal = useSignalStore((state) => state.currentSignal);
  const isResolving = useSignalStore((state) => state.isResolving);
  const fetchPendingSignals = useSignalStore((state) => state.fetchPendingSignals);
  const dismissCurrent = useSignalStore((state) => state.dismissCurrent);
  const resolveAll = useSignalStore((state) => state.resolveAll);
  const nextSignal = useSignalStore((state) => state.nextSignal);
  const prevSignal = useSignalStore((state) => state.prevSignal);

  useEffect(() => {
    fetchPendingSignals();
  }, [fetchPendingSignals]);

  const currentIndex = currentSignal
    ? pendingSignals.findIndex((s) => s.id === currentSignal.id)
    : 0;

  const validIndex = Math.max(0, currentIndex);
  const hasPrev = validIndex > 0;
  const hasNext = validIndex < pendingSignals.length - 1;

  const handleOpenSource = () => {
    if (currentSignal?.source_url && window.ekkoAPI?.openExternal) {
      window.ekkoAPI.openExternal(currentSignal.source_url);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-2 select-none relative">
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
              currentIndex={validIndex}
              totalCount={totalCount || pendingSignals.length}
              hasPrev={hasPrev}
              hasNext={hasNext}
              isResolving={isResolving}
              onPrev={prevSignal}
              onNext={nextSignal}
              onDismiss={() => dismissCurrent('discard')}
              onArchive={() => dismissCurrent('archive')}
              onDismissAll={() => resolveAll('discard')}
              onOpenSource={handleOpenSource}
            />
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex flex-col items-center justify-center gap-1.5 text-center p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]"
          >
            <CheckCircle2 className="w-7 h-7 text-emerald-400/80 mb-0.5" />
            <span className="text-xs font-semibold text-slate-200">
              Radar up to date · No blindspots detected
            </span>
            <p className="text-[11px] text-slate-400 max-w-[280px]">
              The daemon scans your sources in the background and will alert you when new signals emerge.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default RadarView;

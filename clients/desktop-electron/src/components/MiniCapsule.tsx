import React from 'react';
import { motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { Mascot } from './Mascot';
import { useViewStore } from '../core/stores/useViewStore';
import { useSignalStore } from '../core/stores/useSignalStore';

/**
 * MiniCapsule provides the 32px collapsed floating notch state.
 * Employs Framer Motion shared layoutId="app-mascot" for seamless morphing.
 * Expands on click or drag-over.
 */
export const MiniCapsule: React.FC = () => {
  const expand = useViewStore((state) => state.expand);
  const setViewMode = useViewStore((state) => state.setViewMode);
  const isTransitioning = useViewStore((state) => state.isTransitioning);
  const signalCount = useSignalStore((state) => state.totalCount);
  const currentSignal = useSignalStore((state) => state.currentSignal);

  const hasSignals = signalCount > 0 || currentSignal !== null;

  const handleExpand = () => {
    if (isTransitioning) return;
    expand();
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    if (isTransitioning) return;
    setViewMode('home');
    expand();
  };

  return (
    <div
      style={{
        WebkitAppRegion: 'no-drag',
        background: 'var(--notch-anchor, #131313)',
      } as React.CSSProperties}
      onClick={handleExpand}
      onDragEnter={handleDragEnter}
      onDragOver={(e) => e.preventDefault()}
      className="group w-[130px] h-8 mx-auto flex items-center justify-between px-3 select-none rounded-b-2xl border-x border-b border-white/[0.08] shadow-[0_4px_16px_rgba(0,0,0,0.5)] cursor-pointer transition-colors hover:border-white/20 overflow-hidden"
      title="Click or drag file to expand Ekko"
    >
      {/* Miniature Mascot Slot with shared layoutId */}
      <motion.div
        layoutId="app-mascot"
        className="w-6 h-6 flex items-center justify-center relative shrink-0"
      >
        <Mascot emotion={hasSignals ? 'alert' : 'idle'} />
      </motion.div>

      {/* Center / Right Indicator: Amber notification dot or chevron expander */}
      <div className="flex items-center gap-1.5 shrink-0">
        {hasSignals && (
          <span
            className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.8)] animate-pulse"
            title={`${signalCount} pending signal(s)`}
          />
        )}
        <ChevronDown
          size={13}
          className="text-slate-400 group-hover:text-slate-200 transition-colors"
        />
      </div>
    </div>
  );
};

export default MiniCapsule;

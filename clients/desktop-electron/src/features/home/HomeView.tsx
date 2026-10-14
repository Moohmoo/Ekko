import React from 'react';
import { motion } from 'framer-motion';
import { Mascot } from '../../components/Mascot';
import { useMascotGaze } from './hooks/useMascotGaze';
import { DropZone } from './components/DropZone';
import { useDropStore } from '../../core/stores/useDropStore';
import { useBufferStore } from '../../core/stores/useBufferStore';
import { useSignalStore } from '../../core/stores/useSignalStore';
import { useViewStore } from '../../core/stores/useViewStore';

/**
 * HomeView presents the interactive desktop pod:
 * - Left pane (~36%): Centered reactive mascot with GPU-accelerated gaze tracking.
 * - Right pane (~64%): Drop & Forget absorption zone and latest buffer note link.
 */
export const HomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);
  const { dropStatus, mascotEmotion, forcedEmotion } = useDropStore();
  const latestNote = useBufferStore((state) => state.latestNote);
  const currentSignal = useSignalStore((state) => state.currentSignal);

  // Derived mascot emotion (prioritizing dev test forcedEmotion, drag/drop state, blindspot alert, idle)
  const displayEmotion =
    forcedEmotion !== null
      ? forcedEmotion
      : dropStatus === 'hover'
      ? 'hover_drop'
      : dropStatus === 'processing'
      ? 'ingesting'
      : dropStatus === 'ready'
      ? 'ready'
      : dropStatus === 'error'
      ? 'error'
      : currentSignal !== null
      ? 'alert'
      : mascotEmotion;

  const { mascotContainerRef, isHoverWoken } = useMascotGaze(displayEmotion === 'alert');

  return (
    <div className="w-full h-full flex gap-4 p-2.5 select-none overflow-hidden relative cursor-default">
      {/* Left Pane (~36% / ~215px) — Vector mascot centered with ambient shine */}
      <div
        ref={mascotContainerRef}
        className="w-[36%] h-full flex items-center justify-center relative shrink-0 cursor-default pointer-events-none"
      >
        <div className="absolute inset-0 bg-radial from-sky-400/[0.04] via-transparent to-transparent pointer-events-none" />
        <motion.div
          layoutId="app-mascot"
          className="w-24 h-24 flex items-center justify-center"
        >
          <Mascot
            emotion={displayEmotion}
            isWokenByHover={isHoverWoken}
          />
        </motion.div>
      </div>

      {/* Right Pane — Drop & Forget absorption zone */}
      <DropZone
        latestNoteTitle={latestNote?.title}
        onNavigateBuffer={() => setViewMode('buffer')}
      />
    </div>
  );
};

export default HomeView;

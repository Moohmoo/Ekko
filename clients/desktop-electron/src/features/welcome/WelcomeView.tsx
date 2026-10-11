import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Mascot } from '../home/Mascot';
import { useViewStore } from '../../core/stores/useViewStore';
import { WELCOME_DURATION_MS, SPRING_BOUNCY } from '../../design-system/tokens';

export const WelcomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);

  useEffect(() => {
    const timer = setTimeout(() => {
      setViewMode('home');
    }, WELCOME_DURATION_MS);

    return () => clearTimeout(timer);
  }, [setViewMode]);

  return (
    <div className="w-full h-full flex items-center justify-center select-none">
      {/* Inner Raised Floating Cartridge - 100% Visual & Silent */}
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.98 }}
        transition={SPRING_BOUNCY}
        className="w-full h-full rounded-2xl bg-[#141824] border border-white/[0.08] flex items-center justify-center relative overflow-hidden shadow-xl"
      >
        {/* Soft background ambient glow */}
        <div className="absolute inset-0 bg-radial from-sky-400/[0.08] via-transparent to-transparent pointer-events-none" />

        {/* Mascot alone at the center, waving hello with right hand */}
        <div className="flex items-center justify-center">
          <Mascot emotion="welcome" />
        </div>
      </motion.div>
    </div>
  );
};

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
    <div className="w-full h-full p-3 flex items-center justify-center select-none">
      {/* Inner Raised Cartridge */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.97 }}
        transition={SPRING_BOUNCY}
        className="w-full h-full rounded-2xl bg-[#141824] border border-white/[0.08] flex items-center justify-center gap-6 px-8 relative overflow-hidden shadow-inner"
      >
        {/* Soft background radial shine */}
        <div className="absolute inset-0 bg-radial from-sky-500/[0.07] via-transparent to-transparent pointer-events-none" />

        {/* Mascot playing Welcome Emotion */}
        <div className="shrink-0 flex items-center justify-center">
          <Mascot emotion="welcome" />
        </div>

        {/* Greeting Label */}
        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15, ...SPRING_BOUNCY }}
          className="flex flex-col items-start gap-1 z-10"
        >
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-slate-100 tracking-tight">
              Coucou, je suis Ekko
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/30">
              v2.0
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed max-w-[260px]">
            Tampon cognitif ambiant & veille locale continue.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping" />
            <span className="text-[11px] text-sky-400/90 font-medium">
              Prêt à absorber vos flux et documents...
            </span>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

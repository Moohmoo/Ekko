import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Mascot } from '../../components/Mascot';
import { useViewStore } from '../../core/stores/useViewStore';
import { WELCOME_DURATION_MS, COLORS } from '../../design-system/tokens';

export const WelcomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);
  const [isAwakened, setIsAwakened] = useState(false);

  useEffect(() => {
    // Reveal smiling face & satellites after physical bounce settles
    const awakenTimer = setTimeout(() => {
      setIsAwakened(true);
    }, 550);

    // Transition smoothly to 'home' at sequence completion
    const exitTimer = setTimeout(() => {
      setViewMode('home');
    }, WELCOME_DURATION_MS);

    return () => {
      clearTimeout(awakenTimer);
      clearTimeout(exitTimer);
    };
  }, [setViewMode]);

  return (
    <div className="w-full h-full flex gap-4 p-2.5 select-none overflow-hidden relative">
      {/* Soft background ambient radial glow */}
      <div className="absolute inset-0 bg-radial from-sky-400/[0.06] via-transparent to-transparent pointer-events-none" />

      {/* Left Column (~36% / ~215px) — Physics Drop Impact & Concentric Echo Waves */}
      <div className="w-[36%] h-full flex items-center justify-center relative shrink-0">
        {/* Soft radial shine matching HomeView positioning */}
        <div className="absolute inset-0 bg-radial from-sky-400/[0.04] via-transparent to-transparent pointer-events-none" />

        {/* Concentric Echo Wave 1 (Triggers at impact t = 340ms) */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{
            scale: [0, 2.2],
            opacity: [0.65, 0],
          }}
          transition={{
            delay: 0.34,
            duration: 0.7,
            ease: [0.22, 1, 0.36, 1],
          }}
          className="absolute w-20 h-20 rounded-full border border-[#00f2fe] pointer-events-none shadow-[0_0_12px_rgba(0,242,254,0.35)]"
        />

        {/* Concentric Echo Wave 2 (Triggers with slight delay at t = 460ms) */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{
            scale: [0, 2.2],
            opacity: [0.45, 0],
          }}
          transition={{
            delay: 0.46,
            duration: 0.7,
            ease: [0.22, 1, 0.36, 1],
          }}
          className="absolute w-20 h-20 rounded-full border border-[#00f2fe]/80 pointer-events-none shadow-[0_0_8px_rgba(0,242,254,0.25)]"
        />

        {/* Droplet Drop & Squash/Stretch Container */}
        <motion.div
          initial={{ y: -110, scaleY: 1.35, scaleX: 0.8 }}
          animate={{
            y: [-110, 0, 0, 0, 0],
            scaleY: [1.35, 1, 0.72, 1.12, 0.96, 1],
            scaleX: [0.8, 1, 1.28, 0.92, 1.04, 1],
          }}
          transition={{
            duration: 0.75,
            times: [0, 0.45, 0.58, 0.72, 0.86, 1],
            ease: 'easeOut',
          }}
          className="relative flex items-center justify-center z-10"
        >
          {/* Phase 1: Pure stylized falling droplet silhouette */}
          <motion.div
            initial={{ opacity: 1 }}
            animate={{ opacity: isAwakened ? 0 : 1 }}
            transition={{ duration: 0.2 }}
            className={`w-[74px] h-[88px] flex items-center justify-center ${isAwakened ? 'pointer-events-none absolute' : 'relative'}`}
          >
            <svg
              viewBox="0 0 100 120"
              className="w-full h-full drop-shadow-[0_6px_14px_rgba(0,242,254,0.18)]"
            >
              <defs>
                <linearGradient id="welcomeDropletGrad" x1="50%" y1="0%" x2="50%" y2="100%">
                  <stop offset="0%" stopColor={COLORS.cyanGlow} />
                  <stop offset="35%" stopColor={COLORS.cyanAccent} />
                  <stop offset="75%" stopColor={COLORS.bluePrimary} />
                  <stop offset="100%" stopColor={COLORS.blueDeep} />
                </linearGradient>
              </defs>
              <path
                d="M 50 10 C 70 32, 92 64, 92 86 C 92 108, 72 116, 50 116 C 28 116, 8 108, 8 86 C 8 64, 30 32, 50 10 Z"
                fill="url(#welcomeDropletGrad)"
                stroke={COLORS.cyanAccent}
                strokeWidth="1.2"
              />
            </svg>
          </motion.div>

          {/* Phase 2: Awakened Mascot waving hello with floating satellites */}
          {isAwakened && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="relative"
            >
              <Mascot emotion="welcome" />
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* Right Column — Cinematic Typographic Reveal « Ekko » */}
      <div className="flex-1 h-full flex flex-col justify-center items-start pl-3 overflow-hidden relative">
        <motion.div
          initial={{ opacity: 0, x: -16, filter: 'blur(8px)' }}
          animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
          transition={{
            delay: 0.4,
            duration: 0.65,
            ease: [0.16, 1, 0.3, 1],
          }}
          className="flex flex-col"
        >
          {/* Main Title: Geometric & Radiant Gradient */}
          <h1 className="text-3xl font-semibold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-100 to-sky-300">
            Ekko
          </h1>

          {/* Discrete Tagline: Monospace & Letter-spaced */}
          <motion.span
            initial={{ opacity: 0, y: 4, filter: 'blur(4px)' }}
            animate={{ opacity: 0.85, y: 0, filter: 'blur(0px)' }}
            transition={{
              delay: 0.55,
              duration: 0.5,
              ease: 'easeOut',
            }}
            className="text-[11px] text-zinc-500 font-mono tracking-widest uppercase mt-1"
          >
            Ambient Cognitive Buffer
          </motion.span>
        </motion.div>
      </div>
    </div>
  );
};

export default WelcomeView;

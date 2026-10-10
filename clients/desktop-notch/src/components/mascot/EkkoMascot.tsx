import React from 'react';
import { motion, AnimatePresence, type Transition } from 'framer-motion';
import type { MascotState } from '../../types';

interface EkkoMascotProps {
  state?: MascotState;
  size?: 'sm' | 'md' | 'lg' | number;
  className?: string;
  onClick?: () => void;
}

export const EkkoMascot: React.FC<EkkoMascotProps> = ({
  state = 'idle',
  size = 'md',
  className = '',
  onClick,
}) => {
  const pixelSize = typeof size === 'number' ? size : size === 'sm' ? 20 : size === 'md' ? 36 : 130;

  // Spring physics tokens
  const springTransition: Transition = {
    type: 'spring',
    stiffness: 380,
    damping: 28,
    mass: 0.8,
  };

  // Body animations depending on state
  const getBodyAnimation = () => {
    switch (state) {
      case 'idle':
        return {
          y: [0, -3, 0],
          scaleY: [1, 1.03, 1],
          scaleX: [1, 0.98, 1],
          transition: { duration: 3.4, repeat: Infinity, ease: 'easeInOut' as const },
        };
      case 'ingestion':
        return {
          scaleX: [1, 1.25, 0.9, 1.05, 1],
          scaleY: [1, 0.75, 1.2, 0.95, 1],
          y: [0, 4, -5, 1, 0],
          transition: { duration: 0.65, ease: 'easeOut' as const },
        };
      case 'investigation':
        return {
          y: [0, -2, 0],
          rotate: [0, -2, 2, 0],
          transition: { duration: 2.2, repeat: Infinity, ease: 'easeInOut' as const },
        };
      case 'alert':
        return {
          y: [0, -8, 0, -4, 0],
          scale: [1, 1.08, 1, 1.03, 1],
          transition: { duration: 0.8, repeat: Infinity, repeatDelay: 1 },
        };
      case 'drawer':
        return {
          y: [0, -3, 0],
          scale: [1, 1.02, 1],
          transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' as const },
        };
      case 'dizzy':
        return {
          rotate: [0, 6, -6, 4, -4, 0],
          transition: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' as const },
        };
    }
  };

  return (
    <motion.div
      className={`relative inline-flex items-center justify-center select-none ${className}`}
      style={{ width: pixelSize, height: (pixelSize * 140) / 120 }}
      onClick={onClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      transition={springTransition}
    >
      {/* Alert Pulsing Aura */}
      {state === 'alert' && (
        <motion.div
          className="absolute inset-0 rounded-full bg-cyan-400/30 blur-xl pointer-events-none"
          animate={{ scale: [1, 1.5, 1], opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        />
      )}

      {/* Investigation Radar Wave */}
      {state === 'investigation' && (
        <motion.div
          className="absolute inset-0 rounded-full border border-cyan-400/40 pointer-events-none"
          animate={{ scale: [0.8, 1.6], opacity: [0.8, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' as const }}
        />
      )}

      <svg
        viewBox="0 0 120 140"
        className="w-full h-full overflow-visible transition-all duration-300"
        style={{
          filter:
            state === 'alert'
              ? 'drop-shadow(0 0 14px rgba(0, 242, 254, 0.85))'
              : 'drop-shadow(0 0 8px rgba(0, 242, 254, 0.45))',
        }}
      >
        <defs>
          <linearGradient id="ekko-mascot-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#0284c7" />
          </linearGradient>
        </defs>

        {/* Mascot Pear Body */}
        <motion.path
          d="M60,16 C60,16 98,66 98,92 C98,114 81,130 60,130 C39,130 22,114 22,92 C22,66 60,16 60,16 Z"
          fill="url(#ekko-mascot-grad)"
          animate={getBodyAnimation()}
          style={{ transformOrigin: '60px 92px' }}
        />

        {/* Left Detached Hand */}
        <motion.ellipse
          cx="14"
          cy="94"
          rx="5.5"
          ry="5.5"
          fill="#38bdf8"
          animate={
            state === 'investigation'
              ? { x: [-1, 2, -1], y: [0, -2, 0] }
              : { y: [0, -2, 0] }
          }
          transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' as const }}
        />

        {/* Right Detached Hand (Waving in Drawer state) */}
        <motion.g style={{ transformOrigin: '106px 94px' }}>
          <motion.ellipse
            cx="106"
            cy="94"
            rx="5.5"
            ry="5.5"
            fill="#38bdf8"
            animate={
              state === 'drawer'
                ? {
                    y: [0, -6, 0, -6, 0],
                    x: [0, 3, -2, 3, 0],
                    rotate: [0, 20, -15, 20, 0],
                  }
                : { y: [0, -2, 0] }
            }
            transition={
              state === 'drawer'
                ? { duration: 1.2, repeat: Infinity, ease: 'easeInOut' as const }
                : { duration: 2.8, repeat: Infinity, ease: 'easeInOut' as const }
            }
          />
        </motion.g>

        {/* Face Features (Eyes and Mouth) */}
        <g id="mascot-face">
          {/* 1. IDLE: Sleeping Eyes */}
          {state === 'idle' && (
            <motion.g
              stroke="#040814"
              strokeWidth="3.2"
              strokeLinecap="round"
              fill="none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            >
              <path d="M43,89 Q49,94 55,89" />
              <path d="M65,89 Q71,94 77,89" />
            </motion.g>
          )}

          {/* 2. INGESTION: Open Eyes & O-mouth */}
          {state === 'ingestion' && (
            <motion.g
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.2 }}
            >
              <circle cx="49" cy="88" r="5.5" fill="#040814" />
              <circle cx="71" cy="88" r="5.5" fill="#040814" />
              <circle cx="60" cy="98" r="4.2" fill="#040814" />
            </motion.g>
          )}

          {/* 3. INVESTIGATION: Scanning Eyes + Magnifying Glass */}
          {state === 'investigation' && (
            <g>
              <motion.g
                fill="#040814"
                animate={{ x: [-3, 3, -3] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' as const }}
              >
                <circle cx="47" cy="86" r="6" />
                <circle cx="69" cy="86" r="6" />
              </motion.g>
              {/* Floating Magnifying Ring */}
              <motion.g
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1, rotate: [0, 8, -4, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' as const }}
                style={{ transformOrigin: '86px 88px' }}
              >
                <circle cx="86" cy="88" r="9" stroke="#040814" strokeWidth="3" fill="none" />
                <line x1="93" y1="95" x2="101" y2="103" stroke="#040814" strokeWidth="3.2" strokeLinecap="round" />
              </motion.g>
            </g>
          )}

          {/* 4. ALERT: Surprised Eyes */}
          {state === 'alert' && (
            <motion.g
              fill="#040814"
              initial={{ scale: 0.5 }}
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: 0.4, repeat: Infinity, repeatDelay: 0.8 }}
              style={{ transformOrigin: '60px 88px' }}
            >
              <circle cx="49" cy="86" r="6.2" />
              <circle cx="71" cy="86" r="6.2" />
              <circle cx="60" cy="99" r="3.5" fill="#040814" />
            </motion.g>
          )}

          {/* 5. DRAWER: Happy Curved Eyes ^ ^ & Smile */}
          {state === 'drawer' && (
            <motion.g
              stroke="#040814"
              strokeWidth="3.2"
              strokeLinecap="round"
              fill="none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2 }}
            >
              <path d="M43,90 Q49,83 55,90" />
              <path d="M65,90 Q71,83 77,90" />
              <path d="M54,97 Q60,102 66,97" strokeWidth="2.5" />
            </motion.g>
          )}

          {/* 6. DIZZY: Crossed Eyes x x */}
          {state === 'dizzy' && (
            <motion.g
              stroke="#040814"
              strokeWidth="2.8"
              strokeLinecap="round"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <line x1="44" y1="84" x2="54" y2="92" />
              <line x1="54" y1="84" x2="44" y2="92" />
              <line x1="66" y1="84" x2="76" y2="92" />
              <line x1="76" y1="84" x2="66" y2="92" />
              <path d="M54,100 Q60,96 66,100" strokeWidth="2.5" fill="none" />
            </motion.g>
          )}
        </g>
      </svg>

      {/* Floating Zzz in Idle state (Large size only) */}
      <AnimatePresence>
        {state === 'idle' && pixelSize > 50 && (
          <motion.div
            className="absolute top-2 right-4 text-cyan-300 font-bold font-mono text-xs pointer-events-none"
            initial={{ opacity: 0, y: 0, scale: 0.6 }}
            animate={{ opacity: [0, 0.8, 0], y: [-2, -14], x: [0, 8] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeOut' as const }}
          >
            z
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default EkkoMascot;

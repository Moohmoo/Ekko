import React from 'react';
import { motion, type Variants } from 'framer-motion';
import {
  COLORS,
  SPRING_BOUNCY,
  type MascotEmotion,
} from '../design-system/tokens';

export type { MascotEmotion };

interface MascotProps {
  emotion?: MascotEmotion;
  className?: string;
  isWokenByHover?: boolean;
}

const bodyVariants: Variants = {
  idle: {
    scale: [1, 1.015, 1],
    scaleX: 1,
    scaleY: 1,
    rotate: 0,
    x: 0,
    y: [0, -2, 0],
    transition: {
      scale: { duration: 3.2, repeat: Infinity, ease: 'easeInOut' },
      y: { duration: 3.2, repeat: Infinity, ease: 'easeInOut' },
      scaleX: { type: 'spring', damping: 15, stiffness: 200 },
      scaleY: { type: 'spring', damping: 15, stiffness: 200 },
      rotate: { duration: 0.3 },
      x: { duration: 0.3 },
    },
  },
  welcome: {
    scale: [1, 1.03, 1],
    scaleX: 1,
    scaleY: 1,
    rotate: [-2, 2, -2],
    x: 0,
    y: [0, -5, 0],
    transition: {
      scale: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
      y: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
      rotate: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
      scaleX: { type: 'spring', damping: 15, stiffness: 200 },
      scaleY: { type: 'spring', damping: 15, stiffness: 200 },
      x: { duration: 0.3 },
    },
  },
  hover_drop: {
    scale: [1, 1.04, 1],
    scaleX: 1,
    scaleY: 1,
    rotate: 0,
    x: 0,
    y: [0, -3, 0],
    transition: {
      scale: { duration: 1.0, repeat: Infinity, ease: 'easeInOut' },
      y: { duration: 1.0, repeat: Infinity, ease: 'easeInOut' },
      scaleX: { type: 'spring', damping: 15, stiffness: 200 },
      scaleY: { type: 'spring', damping: 15, stiffness: 200 },
      rotate: { duration: 0.3 },
      x: { duration: 0.3 },
    },
  },
  ingesting: {
    scale: 1,
    scaleX: [1, 1.15, 0.85, 1.05, 1],
    scaleY: [1, 0.75, 1.25, 0.95, 1],
    rotate: 0,
    x: 0,
    y: [0, -3, 4, -2, 0],
    transition: {
      scaleX: { duration: 0.9, repeat: Infinity, ease: 'easeInOut' },
      scaleY: { duration: 0.9, repeat: Infinity, ease: 'easeInOut' },
      y: { duration: 0.9, repeat: Infinity, ease: 'easeInOut' },
      scale: { duration: 0.3 },
      rotate: { duration: 0.3 },
      x: { duration: 0.3 },
    },
  },
  ready: {
    scale: [1, 1.05, 1],
    scaleX: 1,
    scaleY: 1,
    rotate: [0, -3, 3, 0],
    x: 0,
    y: [0, -4, 0],
    transition: {
      scale: { duration: 0.8, ease: 'easeInOut' },
      y: { duration: 0.8, ease: 'easeInOut' },
      rotate: { duration: 0.8, ease: 'easeInOut' },
      scaleX: { type: 'spring', damping: 15, stiffness: 200 },
      scaleY: { type: 'spring', damping: 15, stiffness: 200 },
      x: { duration: 0.3 },
    },
  },
  alert: {
    scale: [1.06, 1.02, 1.04, 1.02],
    scaleX: 1,
    scaleY: 1,
    rotate: 0,
    x: 0,
    y: [-4, 0, -3, 0],
    transition: {
      scale: { duration: 1.8, repeat: Infinity, ease: 'easeInOut' },
      y: { duration: 1.8, repeat: Infinity, ease: 'easeInOut' },
      scaleX: { type: 'spring', damping: 15, stiffness: 200 },
      scaleY: { type: 'spring', damping: 15, stiffness: 200 },
      rotate: { duration: 0.3 },
      x: { duration: 0.3 },
    },
  },
  error: {
    scale: 1,
    scaleX: 1,
    scaleY: 1,
    rotate: 0,
    x: [0, -6, 6, -4, 4, 0],
    y: 0,
    transition: {
      x: { duration: 0.35, ease: 'easeInOut' },
      scaleX: { type: 'spring', damping: 15, stiffness: 200 },
      scaleY: { type: 'spring', damping: 15, stiffness: 200 },
      scale: { duration: 0.3 },
      y: { duration: 0.3 },
      rotate: { duration: 0.3 },
    },
  },
};

export const Mascot: React.FC<MascotProps> = React.memo(({
  emotion = 'idle',
  className = '',
  isWokenByHover = false,
}) => {
  // Track render count on window for automated zero-rerender verification in E2E tests
  if (typeof window !== 'undefined') {
    (window as any).__mascotRenderCount = ((window as any).__mascotRenderCount || 0) + 1;
  }

  // Halo Glow variation based on emotion
  const haloScale =
    emotion === 'hover_drop'
      ? [1.1, 1.25, 1.1]
      : [0.95, 1.05, 0.95];
  const haloOpacity =
    emotion === 'hover_drop'
      ? [0.35, 0.5, 0.35]
      : emotion === 'error'
      ? [0.8, 1.0, 0.8]
      : [0.15, 0.25, 0.15];
  const haloColor =
    emotion === 'error'
      ? COLORS.coralGlow
      : emotion === 'ready'
      ? COLORS.emeraldOnline
      : COLORS.cyanGlow;

  // Awake calculation
  const isAwake = emotion !== 'idle' || isWokenByHover;

  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* Pulsing Ambient Glow */}
      <motion.div
        animate={{
          scale: haloScale,
          opacity: haloOpacity,
        }}
        transition={{
          duration: emotion === 'hover_drop' ? 1.5 : 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{ backgroundColor: haloColor }}
        className="absolute w-24 h-24 rounded-full blur-xl pointer-events-none transition-colors duration-500"
      />

      {/* Main Body Animation with guaranteed geometric reset */}
      <motion.div
        id="mascot-body"
        variants={bodyVariants}
        animate={emotion}
        className="relative z-10 w-[74px] h-[88px] flex items-center justify-center"
      >
        {/* Floating Sleep 'z' particle when idle (only if not woken by hover) */}
        {emotion === 'idle' && !isWokenByHover && (
          <motion.div
            initial={{ opacity: 0, y: 0, x: 0, scale: 0.8 }}
            animate={{
              opacity: [0, 0.65, 0],
              y: [-2, -18],
              x: [0, 6],
              scale: [0.8, 1.15],
            }}
            transition={{
              duration: 2.4,
              repeat: Infinity,
              ease: 'easeOut',
            }}
            className="absolute -top-1 right-2 text-[10px] font-bold text-sky-300/70 select-none pointer-events-none"
          >
            z
          </motion.div>
        )}

        {/* Floating Neon Document during Ingestion (Absorbed into O-mouth) */}
        {emotion === 'ingesting' && (
          <motion.div
            initial={{ y: -30, opacity: 0, scale: 0.9, rotate: -6 }}
            animate={{
              y: [-28, 12],
              opacity: [0, 1, 0.8, 0],
              scale: [1, 0.85, 0.45, 0],
              rotate: [-6, 4, 0],
            }}
            transition={{
              duration: 0.9,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
            className="absolute z-20 pointer-events-none flex items-center justify-center"
          >
            <div className="w-[12px] h-[16px] rounded-[3px] bg-sky-950/80 border border-sky-300 shadow-[0_0_8px_rgba(56,189,248,0.7)] flex flex-col justify-center gap-[2px] p-[2px]">
              <div className="w-full h-[1.5px] bg-sky-300 rounded-full" />
              <div className="w-2/3 h-[1.5px] bg-sky-400 rounded-full" />
            </div>
          </motion.div>
        )}

        <svg
          viewBox="0 0 100 120"
          className="w-full h-full drop-shadow-[0_6px_14px_rgba(0,242,254,0.18)]"
        >
          <defs>
            <linearGradient id="ekkoMascotGradient" x1="50%" y1="0%" x2="50%" y2="100%">
              <stop
                offset="0%"
                stopColor={
                  emotion === 'error'
                    ? COLORS.coralGradientTop
                    : emotion === 'ready'
                    ? COLORS.emeraldLight
                    : COLORS.cyanGlow
                }
              />
              <stop
                offset="35%"
                stopColor={
                  emotion === 'error'
                    ? COLORS.coralGradientMid
                    : emotion === 'ready'
                    ? COLORS.emeraldOnline
                    : COLORS.cyanAccent
                }
              />
              <stop
                offset="75%"
                stopColor={
                  emotion === 'error' ? COLORS.coralGradientBottom : COLORS.bluePrimary
                }
              />
              <stop
                offset="100%"
                stopColor={
                  emotion === 'error' ? COLORS.coralGradientBottom : COLORS.blueDeep
                }
              />
            </linearGradient>
          </defs>

          {/* Organic Continuous Pear Droplet Contour — Always pure native blue/cyan on alert */}
          <path
            d="M 50 10 
               C 70 32, 92 64, 92 86 
               C 92 108, 72 116, 50 116 
               C 28 116, 8 108, 8 86 
               C 8 64, 30 32, 50 10 Z"
            fill="url(#ekkoMascotGradient)"
            stroke={
              emotion === 'error'
                ? COLORS.coralAccent
                : emotion === 'ready'
                ? COLORS.emeraldLight
                : COLORS.cyanAccent
            }
            strokeWidth="1.2"
          />

          {/* Attentive Raised Eyebrows for Alert emotion */}
          {emotion === 'alert' && (
            <g stroke={COLORS.eyeDark} strokeWidth="1.4" strokeLinecap="round" fill="none">
              <path d="M 34 50 Q 40 45 46 49" />
              <path d="M 54 49 Q 60 45 66 50" />
            </g>
          )}

          {!isAwake ? (
            /* Sleepy closed eyes curves (‿ ‿) */
            <g stroke={COLORS.eyeDark} strokeWidth="2.2" strokeLinecap="round" fill="none">
              <path d="M 35 63 Q 40 68 45 63" />
              <path d="M 55 63 Q 60 68 65 63" />
            </g>
          ) : (
            /* Expressive open eyes with GPU-accelerated interactive pupil tracking via CSS variables */
            <g
              id="mascot-pupils"
              fill={COLORS.eyeDark}
              style={{
                transform:
                  emotion === 'alert'
                    ? 'translate3d(-3.2px, -2.8px, 0)'
                    : 'translate3d(var(--eye-dx, 0px), var(--eye-dy, 0px), 0)',
                willChange: 'transform',
              }}
            >
              <ellipse
                cx={40}
                cy={62}
                rx={emotion === 'alert' ? 5.2 : emotion === 'hover_drop' ? 4.5 : 3.5}
                ry={emotion === 'alert' ? 6.8 : emotion === 'hover_drop' ? 6 : emotion === 'error' ? 2.2 : 5}
              />
              {emotion !== 'error' && (
                <circle
                  cx={39}
                  cy={60}
                  r={emotion === 'alert' ? 1.8 : emotion === 'hover_drop' ? 1.6 : 1.2}
                  fill={COLORS.white}
                />
              )}

              <ellipse
                cx={60}
                cy={62}
                rx={emotion === 'alert' ? 5.2 : emotion === 'hover_drop' ? 4.5 : 3.5}
                ry={emotion === 'alert' ? 6.8 : emotion === 'hover_drop' ? 6 : emotion === 'error' ? 2.2 : 5}
              />
              {emotion !== 'error' && (
                <circle
                  cx={59}
                  cy={60}
                  r={emotion === 'alert' ? 1.8 : emotion === 'hover_drop' ? 1.6 : 1.2}
                  fill={COLORS.white}
                />
              )}
            </g>
          )}

          {/* Welcoming or Ready Smile */}
          {(emotion === 'welcome' || emotion === 'ready') && (
            <path
              d="M 44 72 Q 50 77 56 72"
              fill="none"
              stroke={COLORS.eyeDark}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          )}

          {/* Ingesting Swallowing Mouth (O-shaped intake) */}
          {emotion === 'ingesting' && (
            <ellipse
              cx="50"
              cy="74"
              rx="4.5"
              ry="5.5"
              fill={COLORS.eyeDark}
            />
          )}

          {/* Surprised "OH!" mouth for alert emotion (:o) */}
          {emotion === 'alert' && (
            <ellipse
              cx="50"
              cy="74"
              rx="2.6"
              ry="3.6"
              fill={COLORS.eyeDark}
            />
          )}

          {/* Annoyed pout mouth for error emotion */}
          {emotion === 'error' && (
            <path
              d="M 44 74 Q 50 70 56 74"
              fill="none"
              stroke={COLORS.eyeDark}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          )}
        </svg>

        {/* Detached Left Satellite Hand */}
        <motion.div
          animate={{
            y: emotion === 'error' ? 0 : emotion === 'ingesting' ? [-3, 3, -3] : [-2, 2, -2],
          }}
          transition={{
            duration: emotion === 'ingesting' ? 0.9 : 2,
            repeat: emotion === 'error' ? 0 : Infinity,
            ease: 'easeInOut',
          }}
          style={{
            backgroundColor:
              emotion === 'error'
                ? COLORS.coralAccent
                : COLORS.cyanAccent,
          }}
          className="absolute -left-2 top-[44px] w-2.5 h-2.5 rounded-full shadow-[0_2px_8px_rgba(56,189,248,0.4)]"
        />

        {/* Detached Right Satellite Hand with Greeting Wave during Welcome */}
        <motion.div
          animate={
            emotion === 'welcome'
              ? {
                  y: [-12, -4, -12],
                  x: [3, 7, 3],
                  rotate: [15, -25, 15],
                  scale: [1, 1.15, 1],
                }
              : emotion === 'ingesting'
              ? {
                  y: [3, -3, 3],
                  x: 0,
                  rotate: 0,
                  scale: 1,
                }
              : emotion === 'error'
              ? {
                  y: 0,
                  x: 0,
                  rotate: 0,
                  scale: 1,
                }
              : {
                  y: [2, -2, 2],
                  x: 0,
                  rotate: 0,
                  scale: 1,
                }
          }
          transition={
            emotion === 'welcome'
              ? {
                  duration: 0.55,
                  repeat: Infinity,
                  ease: 'easeInOut',
                  ...SPRING_BOUNCY,
                }
              : {
                  duration: emotion === 'ingesting' ? 0.9 : 2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }
          }
          style={{
            backgroundColor:
              emotion === 'error'
                ? COLORS.coralAccent
                : COLORS.cyanAccent,
          }}
          className="absolute -right-2 top-[44px] w-2.5 h-2.5 rounded-full shadow-[0_2px_8px_rgba(56,189,248,0.5)] origin-bottom"
        />
      </motion.div>
    </div>
  );
});



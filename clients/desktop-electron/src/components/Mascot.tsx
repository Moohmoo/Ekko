import React from 'react';
import { motion } from 'framer-motion';
import {
  COLORS,
  SPRING_BOUNCY,
  type MascotEmotion,
} from '../design-system/tokens';
import { bodyVariants } from './mascotVariants';

export type { MascotEmotion };

interface MascotProps {
  emotion?: MascotEmotion;
  className?: string;
  isWokenByHover?: boolean;
}

/**
 * Mascot presents the living cognitive companion of Ekko.
 * Decoupled vector rendering: adapts to 100% of container dimensions with zero fixed pixels.
 */
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
      ? [1.05, 1.2, 1.05]
      : [0.95, 1.05, 0.95];
  const haloOpacity =
    emotion === 'hover_drop'
      ? [0.35, 0.5, 0.35]
      : emotion === 'error'
      ? [0.7, 0.9, 0.7]
      : [0.15, 0.25, 0.15];
  const haloColor =
    emotion === 'error'
      ? COLORS.coralGlow
      : emotion === 'ready'
      ? COLORS.emeraldOnline
      : COLORS.cyanGlow;

  // Awake state
  const isAwake = emotion !== 'idle' || isWokenByHover;

  return (
    <div className={`relative w-full h-full flex items-center justify-center ${className}`}>
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
        className="absolute inset-0 rounded-full blur-xl pointer-events-none transition-colors duration-500"
      />

      {/* Main Body Animation with guaranteed geometric reset */}
      <motion.div
        id="mascot-body"
        variants={bodyVariants}
        animate={emotion}
        className="relative z-10 w-full h-full flex items-center justify-center"
      >
        {/* Floating Sleep 'z' particle when idle (only if not woken by hover) */}
        {emotion === 'idle' && !isWokenByHover && (
          <motion.div
            initial={{ opacity: 0, y: 0, x: 0, scale: 0.8 }}
            animate={{
              opacity: [0, 0.65, 0],
              y: [-2, -16],
              x: [0, 5],
              scale: [0.8, 1.15],
            }}
            transition={{
              duration: 2.4,
              repeat: Infinity,
              ease: 'easeOut',
            }}
            className="absolute top-1 right-2 text-[10px] font-bold text-sky-300/70 select-none pointer-events-none"
          >
            z
          </motion.div>
        )}

        {/* Floating Neon Document during Ingestion (Absorbed into O-mouth) */}
        {emotion === 'ingesting' && (
          <motion.div
            initial={{ y: -24, opacity: 0, scale: 0.9, rotate: -6 }}
            animate={{
              y: [-24, 10],
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
            <div className="w-[11px] h-[15px] rounded-[3px] bg-sky-950/80 border border-sky-300 shadow-[0_0_8px_rgba(56,189,248,0.7)] flex flex-col justify-center gap-[2px] p-[2px]">
              <div className="w-full h-[1.5px] bg-sky-300 rounded-full" />
              <div className="w-2/3 h-[1.5px] bg-sky-400 rounded-full" />
            </div>
          </motion.div>
        )}

        <svg
          viewBox="0 0 100 100"
          className="w-full h-full drop-shadow-[0_4px_12px_rgba(0,242,254,0.18)]"
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

          {/* Organic Pear Droplet Contour — Scaled and centered in 100x100 viewBox */}
          <path
            d="M 50 8 C 68 26, 86 52, 86 70 C 86 88, 70 94, 50 94 C 30 94, 14 88, 14 70 C 14 52, 32 26, 50 8 Z"
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
              <path d="M 34 39 Q 40 34 46 38" />
              <path d="M 54 38 Q 60 34 66 39" />
            </g>
          )}

          {!isAwake ? (
            /* Sleepy closed eyes curves (‿ ‿) */
            <g stroke={COLORS.eyeDark} strokeWidth="2.2" strokeLinecap="round" fill="none">
              <path d="M 35 51 Q 40 56 45 51" />
              <path d="M 55 51 Q 60 56 65 51" />
            </g>
          ) : (
            /* Expressive open eyes with GPU-accelerated interactive pupil tracking via CSS variables */
            <g
              id="mascot-pupils"
              fill={COLORS.eyeDark}
              style={{
                transform:
                  emotion === 'alert'
                    ? 'translate3d(-4px, -5px, 0)'
                    : 'translate3d(var(--eye-dx, 0px), var(--eye-dy, 0px), 0)',
                willChange: 'transform',
              }}
            >
              <ellipse
                cx={40}
                cy={50}
                rx={emotion === 'alert' ? 5.2 : emotion === 'hover_drop' ? 4.5 : 3.5}
                ry={emotion === 'alert' ? 6.8 : emotion === 'hover_drop' ? 6 : emotion === 'error' ? 2.2 : 5}
              />
              {emotion !== 'error' && (
                <circle
                  cx={emotion === 'alert' ? 38.5 : 39}
                  cy={emotion === 'alert' ? 47.5 : 48}
                  r={emotion === 'alert' ? 1.8 : emotion === 'hover_drop' ? 1.6 : 1.2}
                  fill="#ffffff"
                />
              )}

              <ellipse
                cx={60}
                cy={50}
                rx={emotion === 'alert' ? 5.2 : emotion === 'hover_drop' ? 4.5 : 3.5}
                ry={emotion === 'alert' ? 6.8 : emotion === 'hover_drop' ? 6 : emotion === 'error' ? 2.2 : 5}
              />
              {emotion !== 'error' && (
                <circle
                  cx={emotion === 'alert' ? 58.5 : 59}
                  cy={emotion === 'alert' ? 47.5 : 48}
                  r={emotion === 'alert' ? 1.8 : emotion === 'hover_drop' ? 1.6 : 1.2}
                  fill="#ffffff"
                />
              )}
            </g>
          )}

          {/* Welcoming or Ready Smile */}
          {(emotion === 'welcome' || emotion === 'ready') && (
            <path
              d="M 44 60 Q 50 65 56 60"
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
              cy="62"
              rx="4.5"
              ry="5.5"
              fill={COLORS.eyeDark}
            />
          )}

          {/* Surprised "OH!" mouth for alert emotion (:o) */}
          {emotion === 'alert' && (
            <ellipse
              cx="50"
              cy="62"
              rx="2.6"
              ry="3.6"
              fill={COLORS.eyeDark}
            />
          )}

          {/* Annoyed pout mouth for error emotion */}
          {emotion === 'error' && (
            <path
              d="M 44 62 Q 50 58 56 62"
              fill="none"
              stroke={COLORS.eyeDark}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          )}

          {/* Detached Left Satellite Hand */}
          <motion.circle
            cx={7}
            cy={50}
            r={3.2}
            animate={{
              cy: emotion === 'error' ? 50 : emotion === 'ingesting' ? [47, 53, 47] : [48, 52, 48],
            }}
            transition={{
              duration: emotion === 'ingesting' ? 0.9 : 2,
              repeat: emotion === 'error' ? 0 : Infinity,
              ease: 'easeInOut',
            }}
            fill={emotion === 'error' ? COLORS.coralAccent : COLORS.cyanAccent}
          />

          {/* Detached Right Satellite Hand with Greeting Wave during Welcome */}
          <motion.g
            animate={
              emotion === 'welcome'
                ? {
                    y: [-8, -2, -8],
                    x: [2, 5, 2],
                    rotate: [15, -25, 15],
                  }
                : emotion === 'ingesting'
                ? { y: [2, -2, 2], x: 0, rotate: 0 }
                : emotion === 'error'
                ? { y: 0, x: 0, rotate: 0 }
                : { y: [2, -2, 2], x: 0, rotate: 0 }
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
          >
            <circle
              cx={93}
              cy={50}
              r={3.2}
              fill={emotion === 'error' ? COLORS.coralAccent : COLORS.cyanAccent}
            />
          </motion.g>
        </svg>
      </motion.div>
    </div>
  );
});

export default Mascot;

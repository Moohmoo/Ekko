import React from 'react';
import { motion } from 'framer-motion';
import {
  COLORS,
  SPRING_BOUNCY,
  type MascotEmotion,
} from '../design-system/tokens';

export type { MascotEmotion };

interface MascotProps {
  emotion?: MascotEmotion;
  className?: string;
  pointerOffset?: { x: number; y: number } | null;
}

export const Mascot: React.FC<MascotProps> = ({
  emotion = 'idle',
  className = '',
  pointerOffset = null,
}) => {
  // Halo Glow variation based on emotion
  const haloScale =
    emotion === 'hover_drop'
      ? [1.1, 1.25, 1.1]
      : emotion === 'alert'
      ? [1.1, 1.3, 1.1]
      : [0.95, 1.05, 0.95];
  const haloOpacity =
    emotion === 'hover_drop'
      ? [0.35, 0.5, 0.35]
      : emotion === 'error'
      ? [0.8, 1.0, 0.8]
      : emotion === 'alert'
      ? [0.55, 0.8, 0.55]
      : [0.15, 0.25, 0.15];
  const haloColor =
    emotion === 'error'
      ? COLORS.coralGlow
      : emotion === 'alert'
      ? COLORS.amberGlow
      : emotion === 'ready'
      ? COLORS.emeraldOnline
      : COLORS.cyanGlow;

  // Eye tracking calculation (strictly bounded to R = 3.5px)
  const isEyeTrackingActive =
    emotion !== 'idle' && emotion !== 'error' && emotion !== 'ingesting';

  let eyeDx = 0;
  let eyeDy = 0;

  if (emotion === 'alert') {
    // Alert posture: gaze naturally oriented rightwards (+3px) towards the sentinel card
    eyeDx = 3.0;
    eyeDy = 0.5;
  } else if (isEyeTrackingActive && pointerOffset) {
    const factor = 0.04;
    const rawDx = pointerOffset.x * factor;
    const rawDy = pointerOffset.y * factor;
    const dist = Math.sqrt(rawDx * rawDx + rawDy * rawDy);
    const maxR = 3.5;
    if (dist > maxR) {
      eyeDx = (rawDx / dist) * maxR;
      eyeDy = (rawDy / dist) * maxR;
    } else {
      eyeDx = rawDx;
      eyeDy = rawDy;
    }
  }

  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      {/* Pulsing Ambient Glow */}
      <motion.div
        animate={{
          scale: haloScale,
          opacity: haloOpacity,
        }}
        transition={{
          duration: emotion === 'hover_drop' ? 1.5 : emotion === 'alert' ? 1.6 : 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{ backgroundColor: haloColor }}
        className="absolute w-24 h-24 rounded-full blur-xl pointer-events-none transition-colors duration-500"
      />

      {/* Main Body Animation (Calibrated ~88px height for pure breathing Coucou minimalism) */}
      <motion.div
        animate={
          emotion === 'welcome'
            ? {
                y: [0, -5, 0],
                rotate: [-2, 2, -2],
                scale: [1, 1.03, 1],
              }
            : emotion === 'ingesting'
            ? {
                y: [0, -3, 4, -2, 0],
                scaleY: [1, 0.75, 1.25, 0.95, 1],
                scaleX: [1, 1.15, 0.85, 1.05, 1],
              }
            : emotion === 'error'
            ? {
                x: [0, -6, 6, -4, 4, 0],
                y: 0,
                scale: 1,
              }
            : emotion === 'alert'
            ? {
                // Initial awaken jolt + attentive presence
                y: [-4, 0, -3, 0],
                scale: [1.06, 1.02, 1.04, 1.02],
              }
            : {
                // Sleepy slow organic breathing
                y: [0, -2, 0],
                scale: [1, 1.015, 1],
              }
        }
        transition={
          emotion === 'welcome'
            ? { duration: 1.2, repeat: Infinity, ease: 'easeInOut' }
            : emotion === 'ingesting'
            ? { duration: 0.9, repeat: Infinity, ease: 'easeInOut' }
            : emotion === 'error'
            ? { duration: 0.35, ease: 'easeInOut' }
            : emotion === 'alert'
            ? { duration: 1.8, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 3.2, repeat: Infinity, ease: 'easeInOut' }
        }
        className="relative z-10 w-[74px] h-[88px] flex items-center justify-center"
      >
        {/* Floating Sleep 'z' particle when idle */}
        {emotion === 'idle' && (
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
                    : emotion === 'alert'
                    ? COLORS.amberAccent
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
                    : emotion === 'alert'
                    ? COLORS.cyanAccent
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

          {/* Organic Continuous Pear Droplet Contour */}
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
                : emotion === 'alert'
                ? COLORS.amberAccent
                : emotion === 'ready'
                ? COLORS.emeraldLight
                : COLORS.cyanAccent
            }
            strokeWidth="1.2"
          />

          {/* Attentive Eyebrows for Alert emotion */}
          {emotion === 'alert' && (
            <g stroke={COLORS.eyeDark} strokeWidth="1.4" strokeLinecap="round" fill="none">
              <path d="M 35 52 Q 40 48 45 51" />
              <path d="M 55 51 Q 60 48 65 52" />
            </g>
          )}

          {/* Eyes rendering according to emotion with smooth gaze offset */}
          {emotion === 'idle' ? (
            /* Sleepy closed eyes curves (‿ ‿) */
            <g stroke={COLORS.eyeDark} strokeWidth="2.2" strokeLinecap="round" fill="none">
              <path d="M 35 63 Q 40 68 45 63" />
              <path d="M 55 63 Q 60 68 65 63" />
            </g>
          ) : (
            /* Expressive open eyes with interactive pupil tracking */
            <g fill={COLORS.eyeDark}>
              <ellipse
                cx={40 + eyeDx}
                cy={62 + eyeDy}
                rx={emotion === 'hover_drop' || emotion === 'alert' ? 4.5 : 3.5}
                ry={emotion === 'hover_drop' || emotion === 'alert' ? 6 : emotion === 'error' ? 2.2 : 5}
              />
              {emotion !== 'error' && (
                <circle
                  cx={39 + eyeDx}
                  cy={60 + eyeDy}
                  r={emotion === 'hover_drop' || emotion === 'alert' ? 1.6 : 1.2}
                  fill={COLORS.white}
                />
              )}

              <ellipse
                cx={60 + eyeDx}
                cy={62 + eyeDy}
                rx={emotion === 'hover_drop' || emotion === 'alert' ? 4.5 : 3.5}
                ry={emotion === 'hover_drop' || emotion === 'alert' ? 6 : emotion === 'error' ? 2.2 : 5}
              />
              {emotion !== 'error' && (
                <circle
                  cx={59 + eyeDx}
                  cy={60 + eyeDy}
                  r={emotion === 'hover_drop' || emotion === 'alert' ? 1.6 : 1.2}
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

          {/* Attentive Curtailed Smile for Alert */}
          {emotion === 'alert' && (
            <path
              d="M 46 72 Q 50 75 54 72"
              fill="none"
              stroke={COLORS.eyeDark}
              strokeWidth="1.4"
              strokeLinecap="round"
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
                : emotion === 'alert'
                ? COLORS.amberAccent
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
                : emotion === 'alert'
                ? COLORS.amberAccent
                : COLORS.cyanAccent,
          }}
          className="absolute -right-2 top-[44px] w-2.5 h-2.5 rounded-full shadow-[0_2px_8px_rgba(56,189,248,0.5)] origin-bottom"
        />
      </motion.div>
    </div>
  );
};



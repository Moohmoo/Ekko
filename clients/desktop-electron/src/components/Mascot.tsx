import React from 'react';
import { motion } from 'framer-motion';
import { SPRING_BOUNCY } from '../design-system/tokens';

export type MascotEmotion = 'welcome' | 'idle' | 'hover_drop' | 'ingesting' | 'ready';

interface MascotProps {
  emotion?: MascotEmotion;
  className?: string;
}

export const Mascot: React.FC<MascotProps> = ({ emotion = 'idle', className = '' }) => {
  // Halo Glow variation based on emotion
  const haloScale = emotion === 'hover_drop' ? [1.1, 1.25, 1.1] : [0.95, 1.05, 0.95];
  const haloOpacity = emotion === 'hover_drop' ? [0.3, 0.45, 0.3] : [0.15, 0.25, 0.15];
  const haloColor = emotion === 'ready' ? '#10b981' : '#00f2fe';

  return (
    <div className={`relative w-36 h-36 flex items-center justify-center ${className}`}>
      {/* Cyan Pulsing Ambient Glow */}
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
        className="absolute w-28 h-28 rounded-full blur-xl pointer-events-none transition-colors duration-500"
      />

      {/* Main Body Animation */}
      <motion.div
        animate={
          emotion === 'welcome'
            ? {
                y: [0, -6, 0],
                rotate: [-2, 2, -2],
                scale: [1, 1.03, 1],
              }
            : emotion === 'ingesting'
            ? {
                y: [0, -2, 4, 0],
                scale: [1, 0.98, 1.04, 1],
              }
            : {
                y: [0, -4, 0],
                scale: [1, 1.02, 1],
              }
        }
        transition={
          emotion === 'welcome'
            ? { duration: 1.2, repeat: Infinity, ease: 'easeInOut' }
            : emotion === 'ingesting'
            ? { duration: 1.0, repeat: Infinity, ease: 'easeInOut' }
            : { duration: 2.5, repeat: Infinity, ease: 'easeInOut' }
        }
        className="relative z-10 w-28 h-32 flex items-center justify-center"
      >
        <svg
          viewBox="0 0 100 120"
          className="w-full h-full drop-shadow-[0_8px_16px_rgba(0,242,254,0.15)]"
        >
          <defs>
            <linearGradient id="ekkoMascotGradient" x1="50%" y1="0%" x2="50%" y2="100%">
              <stop offset="0%" stopColor={emotion === 'ready' ? '#34d399' : '#00f2fe'} />
              <stop offset="35%" stopColor={emotion === 'ready' ? '#10b981' : '#38bdf8'} />
              <stop offset="75%" stopColor="#0284c7" />
              <stop offset="100%" stopColor="#1e3a8a" />
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
            stroke={emotion === 'ready' ? '#34d399' : '#38bdf8'}
            strokeWidth="1.2"
          />

          {/* Expressive Almond Eyes */}
          <g fill="#040814">
            <ellipse
              cx="40"
              cy="62"
              rx={emotion === 'hover_drop' ? 4.5 : 3.5}
              ry={emotion === 'hover_drop' ? 6 : 5}
            />
            <circle cx="39" cy="60" r={emotion === 'hover_drop' ? 1.6 : 1.2} fill="#ffffff" />

            <ellipse
              cx="60"
              cy="62"
              rx={emotion === 'hover_drop' ? 4.5 : 3.5}
              ry={emotion === 'hover_drop' ? 6 : 5}
            />
            <circle cx="59" cy="60" r={emotion === 'hover_drop' ? 1.6 : 1.2} fill="#ffffff" />
          </g>

          {/* Welcoming or Ready Smile */}
          {(emotion === 'welcome' || emotion === 'ready') && (
            <path
              d="M 44 72 Q 50 77 56 72"
              fill="none"
              stroke="#040814"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          )}
        </svg>

        {/* Detached Left Satellite Hand */}
        <motion.div
          animate={{
            y: [-3, 3, -3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute -left-2 top-[60px] w-3.5 h-3.5 rounded-full bg-[#38bdf8] shadow-[0_2px_8px_rgba(56,189,248,0.4)]"
        />

        {/* Detached Right Satellite Hand with Greeting Wave during Welcome */}
        <motion.div
          animate={
            emotion === 'welcome'
              ? {
                  y: [-16, -6, -16],
                  x: [4, 10, 4],
                  rotate: [15, -25, 15],
                  scale: [1, 1.2, 1],
                }
              : {
                  y: [3, -3, 3],
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
                  duration: 2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }
          }
          className="absolute -right-2 top-[60px] w-3.5 h-3.5 rounded-full bg-[#38bdf8] shadow-[0_2px_8px_rgba(56,189,248,0.5)] origin-bottom"
        />
      </motion.div>
    </div>
  );
};


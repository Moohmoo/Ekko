import React from 'react';
import { motion } from 'framer-motion';

export const Mascot: React.FC = () => {
  return (
    <div className="relative w-36 h-36 flex items-center justify-center">
      {/* Soft Cyan Pulsing Ambient Glow */}
      <motion.div
        animate={{
          scale: [0.95, 1.05, 0.95],
          opacity: [0.15, 0.25, 0.15],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="absolute w-28 h-28 rounded-full bg-[#00f2fe] blur-xl pointer-events-none"
      />

      {/* Breathing Main Body Animation */}
      <motion.div
        animate={{
          y: [0, -4, 0],
          scale: [1, 1.02, 1],
        }}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="relative z-10 w-28 h-32 flex items-center justify-center"
      >
        <svg
          viewBox="0 0 100 120"
          className="w-full h-full drop-shadow-[0_8px_16px_rgba(0,242,254,0.15)]"
        >
          <defs>
            <linearGradient id="ekkoMascotGradient" x1="50%" y1="0%" x2="50%" y2="100%">
              <stop offset="0%" stopColor="#00f2fe" />
              <stop offset="35%" stopColor="#38bdf8" />
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
            stroke="#38bdf8"
            strokeWidth="1.2"
          />

          {/* Expressive Almond Eyes */}
          <g fill="#040814">
            <ellipse cx="40" cy="62" rx="3.5" ry="5" />
            <circle cx="39" cy="60" r="1.2" fill="#ffffff" />

            <ellipse cx="60" cy="62" rx="3.5" ry="5" />
            <circle cx="59" cy="60" r="1.2" fill="#ffffff" />
          </g>
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

        {/* Detached Right Satellite Hand */}
        <motion.div
          animate={{
            y: [3, -3, 3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute -right-2 top-[60px] w-3.5 h-3.5 rounded-full bg-[#38bdf8] shadow-[0_2px_8px_rgba(56,189,248,0.4)]"
        />
      </motion.div>
    </div>
  );
};

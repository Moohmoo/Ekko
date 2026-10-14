import React from 'react';
import { motion } from 'framer-motion';
import { SPRING_SNAPPY, SPRING_BOUNCY, COLORS, SURFACES, GRADIENTS } from '../design-system/tokens';

interface PodShellProps {
  targetHeight: number;
  header: React.ReactNode;
  children: React.ReactNode;
}

/**
 * PodShell provides the ambient OLED notch container, organic GNOME top-bar fillets,
 * and height-morphing spring physics.
 */
export const PodShell: React.FC<PodShellProps> = ({
  targetHeight,
  header,
  children,
}) => {
  return (
    <div className="relative w-[620px] mx-auto select-none pt-0">
      {/* Left concave fillet: seamless organic transition from horizontal GNOME bar to notch vertical flank */}
      <svg
        className="absolute top-0 -left-5 w-[21px] h-5 pointer-events-none select-none z-10"
        viewBox="0 0 21 20"
        fill="none"
        aria-hidden="true"
      >
        <path d="M 0 0 A 20 20 0 0 1 20 20 H 21 V 0 H 0 Z" fill="var(--notch-anchor, #131313)" />
        <path
          d="M 0 0 A 20 20 0 0 1 20 20"
          stroke={COLORS.borderDefault}
          strokeWidth="1"
          fill="none"
        />
      </svg>

      {/* Right concave fillet: symmetric seamless organic transition to top panel */}
      <svg
        className="absolute top-0 -right-5 w-[21px] h-5 pointer-events-none select-none z-10"
        viewBox="0 0 21 20"
        fill="none"
        aria-hidden="true"
      >
        <path d="M 1 20 A 20 20 0 0 1 21 0 H 0 V 20 H 1 Z" fill="var(--notch-anchor, #131313)" />
        <path
          d="M 1 20 A 20 20 0 0 1 21 0"
          stroke={COLORS.borderDefault}
          strokeWidth="1"
          fill="none"
        />
      </svg>

      {/* Notch core container: seamless top edge, rounded bottom, spring height morphing */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, height: targetHeight }}
        transition={{
          opacity: SPRING_BOUNCY,
          height: SPRING_SNAPPY,
        }}
        className={`w-full ${SURFACES.shell} rounded-b-[22px] rounded-t-none border-t-0 flex flex-col p-2.5 text-slate-100 overflow-hidden`}
        style={{
          borderTop: 'none',
          background: GRADIENTS.notchBlend,
        }}
      >
        {header}

        {/* Unified Stage: Single inner surface with direct, natural transitions */}
        <div className="flex-1 flex flex-col mt-1.5 rounded-2xl bg-surface border border-white/[0.08] shadow-inner relative overflow-hidden">
          {children}
        </div>
      </motion.div>
    </div>
  );
};

/**
 * Design system tokens: Color palette, layout metrics, and Framer Motion spring physics.
 */

export const COLORS = {
  bgOled: '#0c0c0e',
  surfaceCard: '#141824',
  surfaceSubtle: '#161a24',
  borderDefault: 'rgba(255, 255, 255, 0.08)',
  borderHighlight: 'rgba(255, 255, 255, 0.15)',
  cyanGlow: '#00f2fe',
  cyanAccent: '#38bdf8',
  bluePrimary: '#0284c7',
  blueDeep: '#1e3a8a',
  emeraldOnline: '#10b981',
  redOffline: '#ef4444',
} as const;

export const LAYOUT = {
  podWidth: 620,
  podHeightCompact: 230,
  podHeightExtended: 460,
  headerHeight: 40,
  borderRadius: 28,
} as const;

export const WELCOME_DURATION_MS = 1800;

export const SPRING_SNAPPY = {
  type: 'spring' as const,
  stiffness: 400,
  damping: 30,
  mass: 0.8,
};

export const SPRING_BOUNCY = {
  type: 'spring' as const,
  stiffness: 260,
  damping: 20,
  mass: 1.0,
};

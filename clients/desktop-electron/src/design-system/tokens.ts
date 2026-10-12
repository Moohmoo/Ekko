/**
 * Design system tokens: Color palette, layout metrics, semantic surface classes, and spring physics.
 * Strict zero-hardcoding policy: all components consume these centralized tokens.
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
  emeraldLight: '#34d399',
  redOffline: '#ef4444',
  eyeDark: '#040814',
  white: '#ffffff',
  // Error & Alert tokens (soft coral & muted brick)
  coralGlow: 'rgba(244, 63, 94, 0.25)',
  coralAccent: '#fb7185',
  coralGradientTop: '#e11d48',
  coralGradientMid: '#9f1239',
  coralGradientBottom: '#4c0519',
  // Proactive Blindspot Alert tokens (warm amber)
  amberGlow: 'rgba(245, 158, 11, 0.20)',
  amberAccent: '#f59e0b',
  surfaceAlert: 'rgba(245, 158, 11, 0.04)',
  borderAlert: 'rgba(245, 158, 11, 0.25)',
} as const;

export type MascotEmotion = 'idle' | 'welcome' | 'hover_drop' | 'ingesting' | 'ready' | 'error' | 'alert';

export const LAYOUT = {
  podWidth: 620,
  podHeightCompact: 230,
  podHeightExtended: 460,
  headerHeight: 32,
  borderRadius: 26,
} as const;

export const WELCOME_DURATION_MS = 1800;
export const RESET_ERROR_DELAY_MS = 2500;

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

/**
 * Reusable surface and border classes for Tailwind
 */
export const SURFACE_CARD = 'bg-white/[0.03] border border-white/[0.06]';
export const SURFACE_CARD_HOVER = 'hover:bg-white/[0.06] hover:border-sky-400/30';
export const BORDER_SUBTLE = 'border-white/[0.08]';
export const ACCENT_CYAN = 'text-sky-400';

export const SURFACES = {
  shell: 'bg-background border-x border-b border-white/[0.08] border-t-0 shadow-2xl',
  stage: 'bg-surface border border-white/[0.08] shadow-inner',
  card: SURFACE_CARD,
  cardHover: SURFACE_CARD_HOVER,
  dropzoneIdle: 'bg-transparent border border-dashed border-white/10 hover:border-sky-400/40 hover:bg-white/[0.02]',
  dropzoneHover: 'border border-dashed border-sky-400/60 bg-sky-500/[0.04]',
  dropzoneProcessing: 'border border-sky-500/30 bg-sky-500/[0.03]',
  dropzoneReady: 'border border-emerald-500/30 bg-emerald-500/[0.04]',
  dropzoneError: 'border border-red-500/30 bg-red-500/[0.04]',
  alertCard: 'bg-amber-500/[0.04] border border-amber-500/25',
  headerTabActive: 'bg-white/[0.08] text-sky-400',
  headerTabInactive: 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.06]',
  modalOverlay: 'bg-black/60 backdrop-blur-md',
  modalContainer: 'bg-surface/95 border border-white/[0.08] shadow-2xl backdrop-blur-xl rounded-2xl',
} as const;

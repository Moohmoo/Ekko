import { create } from 'zustand';
import type { ViewMode } from '../types';
import { LAYOUT } from '../../design-system/tokens';

interface ViewState {
  viewMode: ViewMode;
  isCollapsed: boolean;
  isTransitioning: boolean;
  setViewMode: (mode: ViewMode) => void;
  collapse: () => void;
  finishCollapse: () => void;
  expand: () => void;
  finishExpand: () => void;
  resetTransition: () => void;
  setCollapsed: (collapsed: boolean) => void;
}

export const useViewStore = create<ViewState>((set, get) => ({
  viewMode: 'welcome',
  isCollapsed: false,
  isTransitioning: false,

  setViewMode: (mode: ViewMode) => {
    if (get().isTransitioning) return;

    set({ viewMode: mode, isCollapsed: false });

    if (typeof window !== 'undefined' && window.ekkoAPI?.resizeWindow) {
      const isCompact = mode === 'welcome' || mode === 'home' || mode === 'radar';
      const targetHeight = isCompact ? LAYOUT.podHeightCompact : LAYOUT.podHeightExtended;
      window.ekkoAPI.resizeWindow(LAYOUT.windowWidth, targetHeight);
    }
  },

  collapse: () => {
    const { isTransitioning, isCollapsed } = get();
    if (isTransitioning || isCollapsed) return;

    // Start curtain collapse animation: keep window bounds at full size during animation
    set({ isCollapsed: true, isTransitioning: true });
  },

  finishCollapse: () => {
    // Called when curtain animation reaches 32px: physically resize window to capsule
    if (typeof window !== 'undefined' && window.ekkoAPI?.resizeWindow) {
      window.ekkoAPI.resizeWindow(LAYOUT.capsuleWidth, LAYOUT.capsuleHeight);
    }
    set({ isTransitioning: false });
  },

  expand: () => {
    const { isTransitioning, isCollapsed, viewMode } = get();
    if (isTransitioning || !isCollapsed) return;

    const isCompact = viewMode === 'welcome' || viewMode === 'home' || viewMode === 'radar';
    const targetHeight = isCompact ? LAYOUT.podHeightCompact : LAYOUT.podHeightExtended;

    // Immediately resize window to full bounds so animation can unfold without clipping
    if (typeof window !== 'undefined' && window.ekkoAPI?.resizeWindow) {
      window.ekkoAPI.resizeWindow(LAYOUT.windowWidth, targetHeight);
    }

    set({ isCollapsed: false, isTransitioning: true });
  },

  finishExpand: () => {
    // Curtain unfold completed: release transition lock
    set({ isTransitioning: false });
  },

  resetTransition: () => {
    set({ isTransitioning: false });
  },

  setCollapsed: (collapsed: boolean) => {
    if (collapsed) {
      get().collapse();
    } else {
      get().expand();
    }
  },
}));

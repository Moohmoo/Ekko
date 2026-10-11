import { create } from 'zustand';
import type { ViewMode } from '../types';
import { LAYOUT } from '../../design-system/tokens';

interface ViewState {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

export const useViewStore = create<ViewState>((set) => ({
  viewMode: 'welcome',
  setViewMode: (mode: ViewMode) => {
    set({ viewMode: mode });

    if (typeof window !== 'undefined' && window.ekkoAPI?.resizeWindow) {
      if (mode === 'welcome' || mode === 'home') {
        window.ekkoAPI.resizeWindow(LAYOUT.podWidth, LAYOUT.podHeightCompact);
      } else {
        window.ekkoAPI.resizeWindow(LAYOUT.podWidth, LAYOUT.podHeightExtended);
      }
    }
  },
}));

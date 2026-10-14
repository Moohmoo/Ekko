import React, { startTransition } from 'react';
import type { ViewMode } from '../core/types';
import { useDaemonStore } from '../core/stores/useDaemonStore';
import { useSoundStore } from '../core/audio/useSoundStore';
import { Droplet, Zap, Settings, Volume2, VolumeX, X } from 'lucide-react';
import { SURFACES } from '../design-system/tokens';

interface PodHeaderProps {
  activeTab: ViewMode;
  onSelectTab: (tab: ViewMode) => void;
  onClose: () => void;
}

export const PodHeader: React.FC<PodHeaderProps> = ({
  activeTab,
  onSelectTab,
  onClose,
}) => {
  const isOnline = useDaemonStore((state) => state.isOnline);
  const isMuted = useSoundStore((state) => state.isMuted);
  const toggleMute = useSoundStore((state) => state.toggleMute);

  const handleTabClick = (tab: ViewMode) => {
    startTransition(() => {
      onSelectTab(tab);
    });
  };

  const handleClose = () => {
    if (window.ekkoAPI?.closeWindow) {
      window.ekkoAPI.closeWindow();
    } else {
      console.warn('[PodHeader] window.ekkoAPI non disponible pour fermer.');
    }
    if (onClose) {
      onClose();
    }
  };

  return (
    <div
      style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
      className="h-8 px-1 flex items-center justify-between select-none shrink-0"
    >
      {/* Navigation Tabs (Left) */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => handleTabClick('home')}
          className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'home'
              ? SURFACES.headerTabActive
              : SURFACES.headerTabInactive
          }`}
          title="Accueil (Bento)"
        >
          <Droplet size={15} />
        </button>


        <button
          onClick={() => handleTabClick('echo')}
          className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'echo'
              ? SURFACES.headerTabActive
              : SURFACES.headerTabInactive
          }`}
          title="Écho (Fiches PKM)"
        >
          <Zap size={15} />
        </button>
      </div>

      {/* Controls & Status (Right: Dot -> Settings -> Sound -> Close) */}
      <div className="flex items-center gap-1">
        {/* 1. Daemon Status Dot (6px diameter) */}
        <span
          className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 mx-1 ${
            isOnline
              ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]'
              : 'bg-rose-500/80 shadow-[0_0_6px_rgba(244,63,94,0.3)]'
          }`}
          title={isOnline ? 'Daemon connecté' : 'Daemon déconnecté'}
        />

        {/* 2. Settings Button */}
        <button
          onClick={() => handleTabClick('settings')}
          className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'settings'
              ? SURFACES.headerTabActive
              : SURFACES.headerTabInactive
          }`}
          title="Réglages & Télémétrie"
        >
          <Settings size={15} />
        </button>

        {/* 3. Sound Toggle Button */}
        <button
          onClick={toggleMute}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] transition-colors"
          title={isMuted ? 'Activer le son' : 'Couper le son'}
        >
          {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
        </button>

        {/* 4. Close Button */}
        <button
          onClick={handleClose}
          className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/[0.06] transition-colors"
          title="Fermer"
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
};


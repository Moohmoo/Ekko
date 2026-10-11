import React from 'react';
import type { ViewMode } from '../core/types';
import { useDaemonStore } from '../core/stores/useDaemonStore';
import { Droplet, MessageSquare, Zap, Settings, X } from 'lucide-react';
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
    <div className="h-8 px-1 flex items-center justify-between select-none shrink-0">
      {/* Navigation Tabs (Left) */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onSelectTab('home')}
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
          onClick={() => onSelectTab('chat')}
          className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'chat'
              ? SURFACES.headerTabActive
              : SURFACES.headerTabInactive
          }`}
          title="Assistant & Chat"
        >
          <MessageSquare size={15} />
        </button>

        <button
          onClick={() => onSelectTab('echo')}
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

      {/* Controls & Status (Right) */}
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onSelectTab('settings')}
          className={`w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'settings'
              ? SURFACES.headerTabActive
              : SURFACES.headerTabInactive
          }`}
          title="Réglages & Télémétrie"
        >
          <Settings size={15} />
        </button>

        <span
          className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 mx-1 ${
            isOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' : 'bg-red-400'
          }`}
          title={isOnline ? 'Daemon connecté' : 'Daemon déconnecté'}
        />

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

import React from 'react';
import type { ViewMode } from '../core/types';
import { useDaemonStore } from '../core/stores/useDaemonStore';
import { Droplet, MessageSquare, Zap, Settings, X } from 'lucide-react';

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
    <div className="h-9 px-1 flex items-center justify-between select-none shrink-0">
      {/* Navigation Tabs (Left) */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onSelectTab('home')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'home'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
          title="Accueil (Bento)"
        >
          <Droplet className="w-4 h-4" />
        </button>

        <button
          onClick={() => onSelectTab('chat')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'chat'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
          title="Assistant & Chat"
        >
          <MessageSquare className="w-4 h-4" />
        </button>

        <button
          onClick={() => onSelectTab('echo')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'echo'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
          title="Écho (Fiches PKM)"
        >
          <Zap className="w-4 h-4" />
        </button>
      </div>

      {/* Controls & Status (Right) */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onSelectTab('settings')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'settings'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
          }`}
          title="Réglages & Télémétrie"
        >
          <Settings className="w-4 h-4" />
        </button>

        <span
          className={`w-2 h-2 rounded-full transition-colors duration-300 ml-1 ${
            isOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' : 'bg-red-400'
          }`}
          title={isOnline ? 'Daemon connecté' : 'Daemon déconnecté'}
        />

        <button
          onClick={handleClose}
          className="p-1 rounded-md text-slate-500 hover:text-slate-300 transition-colors ml-1"
          title="Fermer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};


import React from 'react';
import { motion } from 'framer-motion';
import type { ViewMode } from '../core/types';
import { useDaemonStore } from '../core/stores/useDaemonStore';
import { useSoundStore } from '../core/audio/useSoundStore';
import { Droplet, MessageSquare, Zap, Settings, Volume2, VolumeX, X } from 'lucide-react';
import { SPRING_SNAPPY } from '../design-system/tokens';

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
          className={`relative w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'home'
              ? 'text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
          }`}
          title="Accueil (Bento)"
        >
          {activeTab === 'home' && (
            <motion.div
              layoutId="activeTabPill"
              transition={SPRING_SNAPPY}
              className="absolute inset-0 rounded-lg bg-white/[0.08]"
            />
          )}
          <span className="relative z-10 flex items-center justify-center">
            <Droplet size={15} />
          </span>
        </button>

        <button
          onClick={() => onSelectTab('chat')}
          className={`relative w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'chat'
              ? 'text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
          }`}
          title="Assistant & Chat"
        >
          {activeTab === 'chat' && (
            <motion.div
              layoutId="activeTabPill"
              transition={SPRING_SNAPPY}
              className="absolute inset-0 rounded-lg bg-white/[0.08]"
            />
          )}
          <span className="relative z-10 flex items-center justify-center">
            <MessageSquare size={15} />
          </span>
        </button>

        <button
          onClick={() => onSelectTab('echo')}
          className={`relative w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'echo'
              ? 'text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
          }`}
          title="Écho (Fiches PKM)"
        >
          {activeTab === 'echo' && (
            <motion.div
              layoutId="activeTabPill"
              transition={SPRING_SNAPPY}
              className="absolute inset-0 rounded-lg bg-white/[0.08]"
            />
          )}
          <span className="relative z-10 flex items-center justify-center">
            <Zap size={15} />
          </span>
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
          onClick={() => onSelectTab('settings')}
          className={`relative w-7 h-7 rounded-lg flex items-center justify-center transition-colors ${
            activeTab === 'settings'
              ? 'text-sky-400'
              : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
          }`}
          title="Réglages & Télémétrie"
        >
          {activeTab === 'settings' && (
            <motion.div
              layoutId="activeTabPill"
              transition={SPRING_SNAPPY}
              className="absolute inset-0 rounded-lg bg-white/[0.08]"
            />
          )}
          <span className="relative z-10 flex items-center justify-center">
            <Settings size={15} />
          </span>
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


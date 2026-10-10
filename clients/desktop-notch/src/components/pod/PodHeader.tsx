import React from 'react';
import { motion } from 'framer-motion';
import { Home, MessageSquare, Sparkles, Settings, Volume2, VolumeX, X } from 'lucide-react';
import type { PodTab } from '../../types';

interface PodHeaderProps {
  activeTab: PodTab;
  onSelectTab: (tab: PodTab) => void;
  onClose: () => void;
  audioMuted: boolean;
  onToggleAudio: () => void;
  daemonConnected: boolean;
}

export const PodHeader: React.FC<PodHeaderProps> = ({
  activeTab,
  onSelectTab,
  onClose,
  audioMuted,
  onToggleAudio,
  daemonConnected,
}) => {
  const navTabs: { id: PodTab; label: string; icon: React.ReactNode }[] = [
    { id: 'home', label: 'Accueil', icon: <Home className="w-4 h-4" /> },
    { id: 'chat', label: 'Assistant', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'echo', label: 'Écho', icon: <Sparkles className="w-4 h-4" /> },
  ];

  return (
    <header className="h-[46px] px-4 border-b border-white/[0.08] flex items-center justify-between select-none bg-black/20">
      {/* Left: Minimal Icon Navigation Group (Style Coucou) */}
      <nav className="flex items-center gap-1 bg-white/[0.04] p-1 rounded-xl border border-white/[0.06]">
        {navTabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`relative p-1.5 rounded-lg transition-colors cursor-pointer ${
                isActive ? 'text-cyan-300' : 'text-slate-400 hover:text-slate-200'
              }`}
              title={tab.label}
              aria-label={tab.label}
            >
              {isActive && (
                <motion.div
                  layoutId="podNavPill"
                  className="absolute inset-0 bg-cyan-500/20 border border-cyan-500/30 rounded-lg shadow-sm"
                  transition={{ type: 'spring', stiffness: 380, damping: 28, mass: 0.8 }}
                />
              )}
              <span className="relative z-10 flex items-center justify-center">
                {tab.icon}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Right: Actions (Settings, Audio Mute, Close/Hide) */}
      <div className="flex items-center gap-1.5 text-slate-400">
        {/* Status Indicator */}
        <span
          className="w-2 h-2 rounded-full mr-1 transition-colors"
          style={{
            backgroundColor: daemonConnected ? '#10b981' : '#f59e0b',
            boxShadow: daemonConnected
              ? '0 0 8px rgba(16, 185, 129, 0.6)'
              : '0 0 8px rgba(245, 158, 11, 0.6)',
          }}
          title={daemonConnected ? 'Daemon local actif' : 'Daemon déconnecté'}
        />

        {/* Audio Toggle */}
        <button
          onClick={onToggleAudio}
          className="p-1.5 rounded-lg hover:bg-white/[0.08] hover:text-slate-200 transition-colors cursor-pointer"
          title={audioMuted ? 'Activer le son' : 'Couper le son'}
          aria-label={audioMuted ? 'Activer le son' : 'Couper le son'}
        >
          {audioMuted ? (
            <VolumeX className="w-3.5 h-3.5 text-slate-500" />
          ) : (
            <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
          )}
        </button>

        {/* Settings Tab */}
        <button
          onClick={() => onSelectTab('settings')}
          className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
            activeTab === 'settings'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'hover:bg-white/[0.08] hover:text-slate-200'
          }`}
          title="Réglages"
          aria-label="Réglages"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>

        {/* Close / Hide Window */}
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-white/[0.08] hover:text-white transition-colors cursor-pointer ml-1"
          title="Masquer le pod"
          aria-label="Masquer le pod"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};

export default PodHeader;

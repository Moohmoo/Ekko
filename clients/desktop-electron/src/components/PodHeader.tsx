import React from 'react';
import type { PodTab } from '../core/types';
import { useDaemonStore } from '../core/stores/useDaemonStore';
import { Droplet, MessageSquare, Layers, X } from 'lucide-react';

interface PodHeaderProps {
  activeTab: PodTab;
  onSelectTab: (tab: PodTab) => void;
  onClose: () => void;
}

export const PodHeader: React.FC<PodHeaderProps> = ({
  activeTab,
  onSelectTab,
  onClose,
}) => {
  const isOnline = useDaemonStore((state) => state.isOnline);

  return (
    <div className="h-10 px-4 flex items-center justify-between border-b border-white/[0.04] bg-[#11141c]/50">
      {/* Navigation Tabs */}
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onSelectTab('home')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'home'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="Accueil"
        >
          <Droplet className="w-4 h-4" />
        </button>

        <button
          onClick={() => onSelectTab('chat')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'chat'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="Assistant"
        >
          <MessageSquare className="w-4 h-4" />
        </button>

        <button
          onClick={() => onSelectTab('echo')}
          className={`p-1.5 rounded-lg transition-colors ${
            activeTab === 'echo'
              ? 'bg-white/10 text-sky-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          title="Écho (Notes)"
        >
          <Layers className="w-4 h-4" />
        </button>
      </div>

      {/* Status Dot & Close Button */}
      <div className="flex items-center gap-3">
        <span
          className={`w-2 h-2 rounded-full transition-colors duration-300 ${
            isOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]' : 'bg-red-400'
          }`}
          title={isOnline ? 'Daemon connecté' : 'Daemon déconnecté'}
        />

        <button
          onClick={onClose}
          className="p-1 rounded-md text-slate-500 hover:text-slate-300 transition-colors"
          title="Fermer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { ShieldCheck, Cpu, HardDrive, RefreshCw } from 'lucide-react';
import type { BYOMProfile, DaemonStatus } from '../../types';

interface SettingsTabProps {
  currentProfile: BYOMProfile;
  onSelectProfile: (profile: BYOMProfile) => void;
  daemonStatus: DaemonStatus;
  onTestPing: () => Promise<void>;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({
  currentProfile,
  onSelectProfile,
  daemonStatus,
  onTestPing,
}) => {
  const [isPinging, setIsPinging] = useState(false);
  const [keepAliveZero, setKeepAliveZero] = useState(true);
  const [nicePriority, setNicePriority] = useState(true);

  const handlePing = async () => {
    setIsPinging(true);
    await onTestPing();
    setTimeout(() => setIsPinging(false), 500);
  };

  return (
    <div className="space-y-3 max-h-[340px] overflow-y-auto pr-1 text-xs">
      {/* BYOM Profile Grid */}
      <div className="bg-slate-900/70 p-3 rounded-xl border border-white/5 space-y-2">
        <span className="font-semibold text-slate-200 block text-[11.5px]">
          Profil Modèle Actuel (BYOM)
        </span>
        <div className="grid grid-cols-3 gap-2">
          {/* Micro */}
          <button
            onClick={() => onSelectProfile('micro')}
            className={`p-2 rounded-lg text-left transition-all duration-200 border ${
              currentProfile === 'micro'
                ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-sm'
                : 'border-white/5 bg-black/20 hover:border-white/20 text-slate-400'
            }`}
          >
            <span className="font-bold block text-[11px]">Micro (1-3B)</span>
            <span className="text-[9.5px] opacity-75">Qwen2.5-1.5B (RAM &lt;3G)</span>
          </button>

          {/* Standard */}
          <button
            onClick={() => onSelectProfile('standard')}
            className={`p-2 rounded-lg text-left transition-all duration-200 border ${
              currentProfile === 'standard'
                ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-sm'
                : 'border-white/5 bg-black/20 hover:border-white/20 text-slate-400'
            }`}
          >
            <span className="font-bold block text-[11px]">Standard (7-14B)</span>
            <span className="text-[9.5px] opacity-75">Qwen2.5-7B (VRAM 8G)</span>
          </button>

          {/* Large */}
          <button
            onClick={() => onSelectProfile('large')}
            className={`p-2 rounded-lg text-left transition-all duration-200 border ${
              currentProfile === 'large'
                ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-sm'
                : 'border-white/5 bg-black/20 hover:border-white/20 text-slate-400'
            }`}
          >
            <span className="font-bold block text-[11px]">Large / API</span>
            <span className="text-[9.5px] opacity-75">Claude / Qwen-32B</span>
          </button>
        </div>
      </div>

      {/* Hardware Confinement Policies */}
      <div className="bg-slate-900/70 p-3 rounded-xl border border-white/5 space-y-2">
        <span className="font-semibold text-slate-200 flex items-center gap-1.5 text-[11.5px]">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          Politique de Confinement Matériel
        </span>

        <label className="flex items-center justify-between text-slate-300 cursor-pointer text-[11px]">
          <div className="flex items-center gap-2">
            <HardDrive className="w-3 h-3 text-slate-500" />
            <span>Décharge VRAM immédiate (keep_alive: 0)</span>
          </div>
          <input
            type="checkbox"
            checked={keepAliveZero}
            onChange={(e) => setKeepAliveZero(e.target.checked)}
            className="accent-cyan-400 rounded cursor-pointer"
          />
        </label>

        <label className="flex items-center justify-between text-slate-300 cursor-pointer text-[11px]">
          <div className="flex items-center gap-2">
            <Cpu className="w-3 h-3 text-slate-500" />
            <span>Priorité réduite processus (nice +10)</span>
          </div>
          <input
            type="checkbox"
            checked={nicePriority}
            onChange={(e) => setNicePriority(e.target.checked)}
            className="accent-cyan-400 rounded cursor-pointer"
          />
        </label>
      </div>

      {/* IPC Socket Health */}
      <div className="bg-slate-900/70 p-3 rounded-xl border border-white/5 flex items-center justify-between">
        <div>
          <span className="font-mono text-[10px] text-slate-500 block">
            Socket IPC Unix Local
          </span>
          <span className="font-mono text-cyan-300 text-[11px]">
            {daemonStatus.socketPath}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`flex items-center gap-1 text-[10.5px] font-mono ${
              daemonStatus.connected ? 'text-emerald-400' : 'text-amber-400'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                daemonStatus.connected
                  ? 'bg-emerald-400 animate-pulse'
                  : 'bg-amber-400'
              }`}
            />
            {daemonStatus.connected ? 'En ligne' : 'Déconnecté'}
          </span>

          <button
            onClick={handlePing}
            disabled={isPinging}
            className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 transition-colors"
            title="Tester le ping IPC"
          >
            <RefreshCw
              className={`w-3 h-3 ${isPinging ? 'animate-spin text-cyan-400' : ''}`}
            />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsTab;

import React, { useState } from 'react';
import { ShieldCheck, Cpu, HardDrive, RefreshCw } from 'lucide-react';
import type { BYOMProfile, DaemonStatus } from '../../types';

interface SettingsViewProps {
  currentProfile: BYOMProfile;
  onSelectProfile: (profile: BYOMProfile) => void;
  daemonStatus: DaemonStatus;
  onTestPing: () => Promise<void>;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
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
    setTimeout(() => setIsPinging(false), 400);
  };

  return (
    <div className="flex-1 flex flex-col p-4 overflow-y-auto space-y-3.5 text-xs">
      {/* BYOM Profile Grid */}
      <div className="bg-white/[0.03] p-3.5 rounded-2xl border border-white/[0.06] space-y-2">
        <span className="font-semibold text-slate-200 block text-[11.5px]">
          Profil Modèle Actuel (BYOM)
        </span>
        <div className="grid grid-cols-3 gap-2">
          {/* Micro */}
          <button
            onClick={() => onSelectProfile('micro')}
            className={`p-2.5 rounded-xl text-left transition-all duration-200 border cursor-pointer ${
              currentProfile === 'micro'
                ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-sm'
                : 'border-white/[0.05] bg-black/20 hover:border-white/20 text-slate-400'
            }`}
          >
            <span className="font-bold block text-[11px]">Micro (1-3B)</span>
            <span className="text-[9.5px] opacity-75">Qwen2.5-1.5B (RAM &lt;3G)</span>
          </button>

          {/* Standard */}
          <button
            onClick={() => onSelectProfile('standard')}
            className={`p-2.5 rounded-xl text-left transition-all duration-200 border cursor-pointer ${
              currentProfile === 'standard'
                ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-sm'
                : 'border-white/[0.05] bg-black/20 hover:border-white/20 text-slate-400'
            }`}
          >
            <span className="font-bold block text-[11px]">Standard (7-14B)</span>
            <span className="text-[9.5px] opacity-75">Mistral-7B (VRAM 8G)</span>
          </button>

          {/* Large */}
          <button
            onClick={() => onSelectProfile('large')}
            className={`p-2.5 rounded-xl text-left transition-all duration-200 border cursor-pointer ${
              currentProfile === 'large'
                ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-sm'
                : 'border-white/[0.05] bg-black/20 hover:border-white/20 text-slate-400'
            }`}
          >
            <span className="font-bold block text-[11px]">Large / API</span>
            <span className="text-[9.5px] opacity-75">Claude / Qwen-32B</span>
          </button>
        </div>
      </div>

      {/* Hardware Confinement Policies */}
      <div className="bg-white/[0.03] p-3.5 rounded-2xl border border-white/[0.06] space-y-2.5">
        <span className="font-semibold text-slate-200 flex items-center gap-1.5 text-[11.5px]">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          Politique de Confinement Matériel
        </span>

        <label className="flex items-center justify-between text-slate-300 cursor-pointer text-[11px]">
          <div className="flex items-center gap-2">
            <HardDrive className="w-3.5 h-3.5 text-slate-500" />
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
            <Cpu className="w-3.5 h-3.5 text-slate-500" />
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

      {/* Unix Socket Health */}
      <div className="bg-white/[0.03] p-3.5 rounded-2xl border border-white/[0.06] flex items-center justify-between">
        <div>
          <span className="font-mono text-[9.5px] text-slate-500 block">
            Socket IPC Unix Local
          </span>
          <span className="font-mono text-cyan-300 text-[11px]">
            {daemonStatus.socketPath}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`flex items-center gap-1 text-[10.5px] font-mono ${
              daemonStatus.connected ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                daemonStatus.connected
                  ? 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]'
                  : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]'
              }`}
            />
            {daemonStatus.connected ? 'Connecté' : 'Déconnecté'}
          </span>

          <button
            onClick={handlePing}
            disabled={isPinging}
            className="p-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] text-slate-300 transition-colors cursor-pointer"
            title="Tester la connexion au socket"
            aria-label="Tester la connexion au socket"
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

export default SettingsView;

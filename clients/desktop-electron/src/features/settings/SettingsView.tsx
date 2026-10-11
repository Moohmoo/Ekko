import React from 'react';
import { useDaemonStore } from '../../core/stores/useDaemonStore';
import { Radio, Cpu, HardDrive, ShieldCheck, Server } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const isOnline = useDaemonStore((state) => state.isOnline);

  return (
    <div className="flex-1 p-3 flex flex-col gap-3 text-xs overflow-y-auto select-none">
      {/* Liaison Daemon & Socket UNIX */}
      <div className="p-3.5 rounded-2xl bg-[#141824] border border-white/[0.08] flex flex-col gap-2.5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-sky-400" />
            <span className="font-semibold text-slate-200">Liaison Daemon Ekko</span>
          </div>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${
              isOnline
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30'
                : 'bg-red-950/40 text-red-300 border-red-500/30'
            }`}
          >
            {isOnline ? 'Connecté' : 'Hors ligne'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-slate-400 pt-1 border-t border-white/[0.04]">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500">Canal IPC UNIX</span>
            <span className="font-mono text-slate-300 text-[11px]">/tmp/ekko.sock</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500">Protocole</span>
            <span className="text-slate-300 text-[11px]">JSON-RPC 2.0 (NDJSON)</span>
          </div>
        </div>
      </div>

      {/* Télémétrie Frugale & Confinement Système */}
      <div className="p-3.5 rounded-2xl bg-[#141824] border border-white/[0.08] flex flex-col gap-2.5 shadow-sm">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-200">Télémétrie & Empreinte Système</span>
        </div>

        <div className="grid grid-cols-3 gap-2 pt-1 border-t border-white/[0.04]">
          <div className="flex flex-col p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500">Allocation VRAM</span>
            <span className="font-mono text-sky-400 font-semibold text-xs mt-0.5">0 MB</span>
            <span className="text-[9px] text-slate-500">Confinement strict</span>
          </div>

          <div className="flex flex-col p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500">Priorité CPU</span>
            <span className="font-mono text-emerald-400 font-semibold text-xs mt-0.5">nice +10</span>
            <span className="text-[9px] text-slate-500">Arrière-plan discret</span>
          </div>

          <div className="flex flex-col p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500">Confinement GPU</span>
            <span className="font-mono text-purple-400 font-semibold text-xs mt-0.5">keep_alive: 0</span>
            <span className="text-[9px] text-slate-500">Purge immédiate</span>
          </div>
        </div>
      </div>

      {/* Veilleurs & Sources de Signal */}
      <div className="p-3.5 rounded-2xl bg-[#141824] border border-white/[0.08] flex flex-col gap-2.5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-amber-400" />
            <span className="font-semibold text-slate-200">Veilleurs Configurés</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">config/sources.yaml</span>
        </div>

        <div className="flex items-center gap-2 pt-1 border-t border-white/[0.04]">
          <div className="flex-1 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-[11px] font-medium text-slate-300">arXiv AI & CS</span>
              <span className="text-[9px] text-slate-500">Flux RSS / XML</span>
            </div>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          </div>

          <div className="flex-1 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-[11px] font-medium text-slate-300">Hacker News</span>
              <span className="text-[9px] text-slate-500">API Algolia (Top Stories)</span>
            </div>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          </div>

          <div className="flex-1 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div className="flex flex-col">
              <span className="text-[11px] font-medium text-slate-300">Flux Tech RSS</span>
              <span className="text-[9px] text-slate-500">Agrégateur local</span>
            </div>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          </div>
        </div>
      </div>

      {/* Profils BYOM & Modèles */}
      <div className="p-3.5 rounded-2xl bg-[#141824] border border-white/[0.08] flex flex-col gap-2 shadow-sm">
        <div className="flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-slate-200">Modèles & Moteur Cognitif (BYOM)</span>
        </div>
        <div className="flex items-center justify-between text-slate-400 pt-1 border-t border-white/[0.04]">
          <span>Moteur de distillation :</span>
          <span className="text-slate-200 font-mono text-[11px]">gemini-2.5-flash / local</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>Gouvernance mémoire :</span>
          <span className="text-emerald-400 font-medium text-[11px] flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> SQLite WAL + FTS5
          </span>
        </div>
      </div>
    </div>
  );
};

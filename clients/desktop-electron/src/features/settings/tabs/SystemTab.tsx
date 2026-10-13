import React from 'react';
import { Server, Cpu, RefreshCw, Database, ShieldCheck } from 'lucide-react';
import type { SystemMetadata } from '../../../core/types';

interface SystemTabProps {
  system: SystemMetadata | null;
  isOnline: boolean;
  isLoading: boolean;
  onRefresh: () => Promise<void>;
}

export const SystemTab: React.FC<SystemTabProps> = ({
  system,
  isOnline,
  isLoading,
  onRefresh,
}) => {
  const dbPath = system?.sqlite_db_path || 'data/ekko.db';
  const socketPath = system?.ipc_socket_path || '/tmp/ekko.sock';

  return (
    <div className="flex flex-col gap-3 text-xs select-none">
      {/* Liaison Daemon & Socket UNIX */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-sky-400" />
            <span className="font-semibold text-slate-200">Liaison Daemon Ekko</span>
          </div>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium border flex items-center gap-1.5 ${
              isOnline
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30'
                : 'bg-red-950/40 text-red-300 border-red-500/30'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-red-400'}`} />
            <span>{isOnline ? 'Connecté' : 'Hors ligne'}</span>
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-slate-400 pt-1 border-t border-white/[0.04]">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500">Canal IPC UNIX</span>
            <span className="font-mono text-slate-300 text-[11px] truncate" title={socketPath}>
              {socketPath}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500">Protocole</span>
            <span className="text-slate-300 text-[11px]">JSON-RPC 2.0 (NDJSON)</span>
          </div>
        </div>
      </div>

      {/* Stockage & Base SQLite */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-400" />
            <span className="font-semibold text-slate-200">Base de Données Locale</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-emerald-400" /> WAL + FTS5
          </span>
        </div>

        <div className="flex flex-col pt-1 border-t border-white/[0.04]">
          <span className="text-[10px] text-slate-500">Emplacement SQLite</span>
          <span className="font-mono text-slate-300 text-[11px] truncate" title={dbPath}>
            {dbPath}
          </span>
        </div>
      </div>

      {/* Confinement Matériel */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-purple-400" />
          <span className="font-semibold text-slate-200">Empreinte Système & Priorité</span>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.04]">
          <div className="flex flex-col p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500">Allocation VRAM</span>
            <span className="font-mono text-sky-400 font-semibold text-xs mt-0.5">0 MB</span>
            <span className="text-[9px] text-slate-500">Purge keep_alive: 0</span>
          </div>

          <div className="flex flex-col p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500">Priorité CPU</span>
            <span className="font-mono text-emerald-400 font-semibold text-xs mt-0.5">nice +10</span>
            <span className="text-[9px] text-slate-500">Discrétion maximale</span>
          </div>
        </div>
      </div>

      {/* Bouton de diagnostic & actualisation */}
      <div className="flex justify-end pt-1">
        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          className="px-3 py-1.5 rounded-xl bg-white/[0.04] text-slate-300 border border-white/[0.08] hover:bg-white/[0.08] hover:text-white transition-colors disabled:opacity-50 flex items-center gap-1.5 text-[11px]"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
          <span>Actualiser la configuration</span>
        </button>
      </div>
    </div>
  );
};

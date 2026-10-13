import React, { useState } from 'react';
import { Cpu, Eye, EyeOff, ShieldCheck, Key, Server } from 'lucide-react';
import type { SystemMetadata } from '../../../core/types';

interface ModelsTabProps {
  system: SystemMetadata | null;
}

export const ModelsTab: React.FC<ModelsTabProps> = ({ system }) => {
  const [showKey, setShowKey] = useState(false);
  const [localEndpoint, setLocalEndpoint] = useState('http://localhost:11434');

  const provider = system?.llm_provider || 'LiteLLM';
  const activeModel = system?.active_model || 'Non configuré';

  return (
    <div className="flex flex-col gap-3 text-xs select-none">
      {/* Provider & Modèle Actif */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-400" />
            <span className="font-semibold text-slate-200">Moteur Cognitif (BYOM)</span>
          </div>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-sky-950/40 text-sky-300 border border-sky-500/30">
            {provider}
          </span>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-white/[0.04]">
          <span className="text-slate-400 text-[11px]">Modèle actif :</span>
          <span className="font-mono text-slate-200 text-[11px] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.04]">
            {activeModel}
          </span>
        </div>
      </div>

      {/* Clé API Cloud */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-amber-400" />
            <span className="font-semibold text-slate-200">Clé d'API Cloud</span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Chargée (.env)</span>
          </div>
        </div>

        <div className="relative flex items-center pt-1 border-t border-white/[0.04]">
          <input
            type={showKey ? 'text' : 'password'}
            readOnly
            value="••••••••••••••••••••••••••••••••"
            className="w-full bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] font-mono text-slate-300 pr-8 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-2 p-1 text-slate-400 hover:text-slate-200 transition-colors"
            title={showKey ? 'Masquer la clé' : 'Afficher la clé'}
          >
            {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Endpoint Local Ollama */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-slate-200">Endpoint Local (Ollama)</span>
        </div>
        <div className="pt-1 border-t border-white/[0.04]">
          <input
            type="text"
            value={localEndpoint}
            onChange={(e) => setLocalEndpoint(e.target.value)}
            placeholder="http://localhost:11434"
            className="w-full bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-sky-500/40"
          />
        </div>
      </div>

      {/* Confinement Matériel & VRAM */}
      <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-slate-400">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-[11px]">Confinement mémoire :</span>
        </div>
        <span className="font-mono text-purple-300 text-[10px]">
          keep_alive: 0 (Purge VRAM)
        </span>
      </div>
    </div>
  );
};

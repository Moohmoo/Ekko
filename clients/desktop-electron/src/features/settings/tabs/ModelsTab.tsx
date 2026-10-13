import React from 'react';
import { Cpu, ShieldCheck, Key, Server, CheckCircle2 } from 'lucide-react';
import type { SystemMetadata } from '../../../core/types';

interface ModelsTabProps {
  system: SystemMetadata | null;
}

export const ModelsTab: React.FC<ModelsTabProps> = ({ system }) => {
  const provider = system?.llm_provider || 'LiteLLM';
  const activeModel = system?.active_model || 'Non configuré';

  return (
    <div className="flex flex-col gap-2.5 text-xs select-none">
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

      {/* Clé API Cloud - Statut Honnête */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-amber-400" />
            <span className="font-semibold text-slate-200">Clé d'API Cloud</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span>Configurée (.env)</span>
          </div>
        </div>

        <div className="pt-1 border-t border-white/[0.04]">
          <p className="text-[11px] text-zinc-500 leading-relaxed">
            Gérée localement dans le fichier <code className="text-zinc-400 font-mono">.env</code> pour préserver vos secrets.
          </p>
        </div>
      </div>

      {/* Endpoint Local Ollama - Statut en Lecture Seule */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-emerald-400" />
            <span className="font-semibold text-slate-200">Endpoint Local (Ollama)</span>
          </div>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-500/30">
            Port standard
          </span>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-white/[0.04]">
          <span className="text-slate-400 text-[11px]">URL du runtime :</span>
          <span className="font-mono text-slate-200 text-[11px] bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.04]">
            http://localhost:11434
          </span>
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

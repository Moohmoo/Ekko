import React, { useState } from 'react';
import { Radio, Plus, Trash2, Rss, Globe } from 'lucide-react';
import type { SourceItem } from '../../../core/types';

interface SourcesTabProps {
  sources: SourceItem[];
  isSaving: boolean;
  onToggleSource: (id: string) => Promise<boolean>;
  onAddRssSource: (id: string, url: string) => Promise<boolean>;
  onRemoveSource: (id: string) => Promise<boolean>;
}

export const SourcesTab: React.FC<SourcesTabProps> = ({
  sources,
  isSaving,
  onToggleSource,
  onAddRssSource,
  onRemoveSource,
}) => {
  const [newId, setNewId] = useState('');
  const [newUrl, setNewUrl] = useState('');

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newId.trim() || !newUrl.trim()) return;
    const success = await onAddRssSource(newId.trim(), newUrl.trim());
    if (success) {
      setNewId('');
      setNewUrl('');
    }
  };

  return (
    <div className="flex flex-col gap-3 text-xs select-none">
      {/* Formulaire d'ajout rapide de flux RSS */}
      <form onSubmit={handleAdd} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <Plus className="w-4 h-4 text-sky-400" />
          <span>Ajouter un flux de veille (RSS)</span>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/[0.04]">
          <input
            type="text"
            value={newId}
            onChange={(e) => setNewId(e.target.value)}
            placeholder="Identifiant (ex: techcrunch)"
            className="bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/40"
          />
          <input
            type="url"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="URL du flux (https://...)"
            className="bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/40"
          />
        </div>

        <div className="flex justify-end pt-1">
          <button
            type="submit"
            disabled={!newId.trim() || !newUrl.trim() || isSaving}
            className="px-3 py-1 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 font-medium text-[11px] hover:bg-sky-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Ajouter la source</span>
          </button>
        </div>
      </form>

      {/* Liste des veilleurs configurés */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-slate-400 px-1">
          <div className="flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-amber-400" />
            <span className="font-semibold text-slate-300">Veilleurs actifs ({sources.length})</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">sources.yaml</span>
        </div>

        {sources.length === 0 ? (
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] text-center text-slate-500 text-[11px]">
            Aucun veilleur configuré.
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {sources.map((source) => {
              const isEnabled = source.enabled !== false;
              return (
                <div
                  key={source.id}
                  className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] transition-colors flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <div className="p-1.5 rounded-lg bg-white/[0.04] text-slate-300 shrink-0">
                      {source.type === 'rss' ? <Rss className="w-3.5 h-3.5 text-amber-400" /> : <Globe className="w-3.5 h-3.5 text-sky-400" />}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-slate-200 text-[11px] truncate">{source.id}</span>
                        <span className="px-1.5 py-0.2 rounded text-[9px] uppercase font-mono bg-white/[0.05] text-slate-400 border border-white/[0.04]">
                          {source.type}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 truncate" title={source.url || source.path || ''}>
                        {source.url || source.path || `Intervalle: ${source.interval || '1h'}`}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Toggle Switch On/Off */}
                    <button
                      type="button"
                      onClick={() => onToggleSource(source.id)}
                      disabled={isSaving}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none disabled:opacity-50 ${
                        isEnabled ? 'bg-emerald-500/80' : 'bg-zinc-700/60'
                      }`}
                      title={isEnabled ? 'Désactiver le veilleur' : 'Activer le veilleur'}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                          isEnabled ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>

                    {/* Bouton Supprimer */}
                    <button
                      type="button"
                      onClick={() => onRemoveSource(source.id)}
                      disabled={isSaving}
                      className="p-1 text-slate-500 hover:text-red-400 transition-colors disabled:opacity-40"
                      title="Supprimer ce veilleur"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

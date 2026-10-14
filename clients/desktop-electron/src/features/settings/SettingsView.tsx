import React, { useState, useEffect } from 'react';
import { Globe, ListFilter, Radio, Plus, Trash2, X, RotateCw, AlertCircle, Rss } from 'lucide-react';
import { useSettingsStore } from '../../core/stores/useSettingsStore';
import { useDaemonStore } from '../../core/stores/useDaemonStore';

export const SettingsView: React.FC = () => {
  const [newTopic, setNewTopic] = useState('');
  const [newId, setNewId] = useState('');
  const [newUrl, setNewUrl] = useState('');

  const {
    settings, userContext, sources, system, isLoading, isSaving, error,
    fetchSettings, saveUserContext, toggleSource, addRssSource, removeSource,
  } = useSettingsStore();
  const isOnline = useDaemonStore((s) => s.isOnline);

  useEffect(() => {
    if (!settings && !isLoading) fetchSettings();
  }, [settings, isLoading, fetchSettings]);

  const activeLang = userContext?.language || userContext?.preferred_language || 'en';
  const topics = userContext?.topics || userContext?.preferences || [];

  const handleLang = (lang: 'en' | 'fr') => saveUserContext({ language: lang, preferred_language: lang });
  const handleRemoveTopic = (t: string) => saveUserContext({ topics: topics.filter((i) => i !== t), preferences: topics.filter((i) => i !== t) });

  const handleAddTopic = (e: React.FormEvent) => {
    e.preventDefault();
    const t = newTopic.trim();
    if (t && !topics.includes(t)) {
      saveUserContext({ topics: [...topics, t], preferences: [...topics, t] });
      setNewTopic('');
    }
  };

  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newId.trim() && newUrl.trim() && await addRssSource(newId.trim(), newUrl.trim())) {
      setNewId('');
      setNewUrl('');
    }
  };

  return (
    <div className="flex-1 p-3 flex flex-col h-full overflow-hidden select-none text-xs">
      {error && (
        <div className="mb-2 p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px] flex items-center gap-2 shrink-0">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
          <span className="truncate flex-1">{error}</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
        {/* 1. Distillation Language */}
        <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold text-slate-200">
            <Globe className="w-3.5 h-3.5 text-sky-400" />
            <span>Distillation Language</span>
          </div>
          <div className="flex bg-black/30 p-0.5 rounded-lg border border-white/[0.06] w-36">
            {(['en', 'fr'] as const).map((lang) => (
              <button key={lang} type="button" onClick={() => handleLang(lang)} className={`flex-1 py-1 rounded-md text-[11px] font-medium transition-colors ${activeLang === lang ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' : 'text-slate-400 hover:text-slate-200'}`}>
                {lang === 'en' ? 'English' : 'Français'}
              </button>
            ))}
          </div>
        </div>

        {/* 2. Radar Topics */}
        <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
          <div className="flex items-center justify-between font-semibold text-slate-200">
            <div className="flex items-center gap-2"><ListFilter className="w-3.5 h-3.5 text-emerald-400" /><span>Radar Topics</span></div>
            <span className="text-[10px] text-slate-500 font-mono font-normal">{topics.length} active</span>
          </div>
          <form onSubmit={handleAddTopic} className="flex gap-1.5">
            <input type="text" value={newTopic} onChange={(e) => setNewTopic(e.target.value)} placeholder="Add topic (e.g. AI, Bio-informatics)..." className="flex-1 bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/40" />
            <button type="submit" disabled={!newTopic.trim() || isSaving} className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-40 flex items-center gap-1 text-[11px]">
              <Plus className="w-3 h-3" /><span>Add</span>
            </button>
          </form>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {topics.map((t) => (
              <span key={t} className="inline-flex items-center gap-1 bg-white/[0.04] border border-white/[0.08] px-2 py-0.5 rounded-md text-[11px] text-zinc-300">
                <span>{t}</span>
                <button type="button" onClick={() => handleRemoveTopic(t)} disabled={isSaving} className="text-slate-500 hover:text-rose-400 p-0.5" title="Remove topic"><X className="w-2.5 h-2.5" /></button>
              </span>
            ))}
            {topics.length === 0 && <span className="text-[10px] text-slate-500 italic">No topics set. Radar ingests all streams.</span>}
          </div>
        </div>

        {/* 3. Watch Sources */}
        <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
          <div className="flex items-center justify-between font-semibold text-slate-200">
            <div className="flex items-center gap-2"><Radio className="w-3.5 h-3.5 text-amber-400" /><span>Watch Sources</span></div>
            <span className="text-[10px] text-slate-500 font-mono font-normal">{sources.length} sources</span>
          </div>
          <form onSubmit={handleAddSource} className="grid grid-cols-[1fr_2fr_auto] gap-1.5">
            <input type="text" value={newId} onChange={(e) => setNewId(e.target.value)} placeholder="ID" className="bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/40" />
            <input type="url" value={newUrl} onChange={(e) => setNewUrl(e.target.value)} placeholder="https://.../feed" className="bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/40" />
            <button type="submit" disabled={!newId.trim() || !newUrl.trim() || isSaving} className="px-2.5 py-1 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 hover:bg-sky-500/30 transition-colors disabled:opacity-40 flex items-center gap-1 text-[11px]">
              <Plus className="w-3 h-3" /><span>Add</span>
            </button>
          </form>
          <div className="flex flex-col gap-1.5 pt-0.5">
            {sources.map((s) => {
              const enabled = s.enabled !== false;
              return (
                <div key={s.id} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <Rss className="w-3 h-3 text-amber-400 shrink-0" />
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-slate-200 text-[11px] truncate">{s.id}</span>
                        <span className="px-1 py-0.2 rounded text-[8.5px] uppercase font-mono bg-white/[0.05] text-slate-400">{s.type}</span>
                      </div>
                      <span className="text-[9.5px] text-slate-500 truncate" title={s.url || s.path || ''}>{s.url || s.path || `Interval: ${s.interval || '1h'}`}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button type="button" onClick={() => toggleSource(s.id)} disabled={isSaving} className={`relative inline-flex h-4 w-7 cursor-pointer rounded-full border border-transparent transition-colors ${enabled ? 'bg-emerald-500/80' : 'bg-zinc-700/60'}`} title={enabled ? 'Disable source' : 'Enable source'}>
                      <span className={`inline-block h-3 w-3 rounded-full bg-white transition ${enabled ? 'translate-x-3.5' : 'translate-x-0.5'}`} />
                    </button>
                    <button type="button" onClick={() => removeSource(s.id)} disabled={isSaving} className="p-1 text-slate-500 hover:text-red-400 transition-colors" title="Remove source"><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Technical Status line */}
      <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400 shrink-0">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-red-400'}`} />
            <span>{isOnline ? 'Connected' : 'Offline'}</span>
          </span>
          <span>·</span>
          <span className="font-mono text-slate-300 text-[10.5px]">{system?.active_model || 'Ollama qwen2.5:7b'}</span>
        </div>
        <button type="button" onClick={() => fetchSettings()} disabled={isLoading} className="p-1 text-slate-400 hover:text-sky-300 transition-colors rounded hover:bg-white/[0.04]" title="Refresh settings">
          <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
        </button>
      </div>
    </div>
  );
};

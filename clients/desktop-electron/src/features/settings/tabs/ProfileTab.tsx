import React, { useState, useEffect } from 'react';
import { Globe, ListFilter, Plus, Trash2, Save, Check, Loader2 } from 'lucide-react';
import type { UserContextConfig } from '../../../core/types';

interface ProfileTabProps {
  userContext: UserContextConfig | null;
  isSaving: boolean;
  onSave: (context: Partial<UserContextConfig>) => Promise<boolean>;
}

export const ProfileTab: React.FC<ProfileTabProps> = ({
  userContext,
  isSaving,
  onSave,
}) => {
  const [language, setLanguage] = useState<'fr' | 'en'>('fr');
  const [topics, setTopics] = useState<string[]>([]);
  const [newTopic, setNewTopic] = useState('');
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    if (userContext) {
      const activeLang = (userContext.language || userContext.preferred_language || 'fr') as 'fr' | 'en';
      setLanguage(activeLang === 'en' ? 'en' : 'fr');
      setTopics(userContext.topics || userContext.preferences || []);
    }
  }, [userContext]);

  const handleAddTopic = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newTopic.trim();
    if (trimmed && !topics.includes(trimmed)) {
      setTopics([...topics, trimmed]);
      setNewTopic('');
    }
  };

  const handleRemoveTopic = (topicToRemove: string) => {
    setTopics(topics.filter((t) => t !== topicToRemove));
  };

  const handleSave = async () => {
    const success = await onSave({
      language,
      preferred_language: language,
      topics,
      preferences: topics,
    });
    if (success) {
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    }
  };

  return (
    <div className="relative flex flex-col select-none text-xs pb-16">
      <div className="flex flex-col gap-2.5">
        {/* Langue de distillation */}
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
          <div className="flex items-center gap-2 text-slate-200 font-semibold">
            <Globe className="w-4 h-4 text-sky-400" />
            <span>Langue de distillation & réponse</span>
          </div>

          <div className="pt-1 border-t border-white/[0.04] flex items-center justify-between">
            <span className="text-[10px] text-slate-400">
              Langue utilisée par le daemon pour synthétiser les signaux et fiches
            </span>
            <div className="flex bg-black/30 p-0.5 rounded-lg border border-white/[0.06] w-48">
              <button
                type="button"
                onClick={() => setLanguage('fr')}
                className={`flex-1 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  language === 'fr'
                    ? 'bg-sky-500/20 text-sky-300 shadow-sm border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Français
              </button>
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`flex-1 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  language === 'en'
                    ? 'bg-sky-500/20 text-sky-300 shadow-sm border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                English
              </button>
            </div>
          </div>
        </div>

        {/* Thématiques prioritaires de veille & Radar */}
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
          <div className="flex items-center justify-between text-slate-200 font-semibold">
            <div className="flex items-center gap-2">
              <ListFilter className="w-4 h-4 text-emerald-400" />
              <span>Thématiques & Filtres Radar</span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">{topics.length} active(s)</span>
          </div>

          {/* Formulaire ajout direct d'une thématique */}
          <form onSubmit={handleAddTopic} className="flex items-center gap-1.5 pt-1 border-t border-white/[0.04]">
            <input
              type="text"
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              placeholder="Ex: Intelligence artificielle, bio-informatique, open-weights..."
              className="flex-1 bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/40"
            />
            <button
              type="submit"
              disabled={!newTopic.trim()}
              className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-40 flex items-center gap-1 text-[11px]"
              title="Ajouter la thématique"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Ajouter</span>
            </button>
          </form>

          {/* Liste des thématiques en cartes */}
          <div className="flex flex-col gap-1.5 pt-1">
            {topics.map((topic, index) => (
              <div
                key={`${topic}-${index}`}
                className="bg-white/[0.02] border border-white/[0.05] rounded-md p-2 text-xs flex justify-between items-start gap-2 hover:border-white/[0.1] transition-colors"
              >
                <span className="text-zinc-300 break-words leading-relaxed text-[11px] flex-1">
                  {topic}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemoveTopic(topic)}
                  className="text-slate-500 hover:text-rose-400 p-0.5 transition-colors shrink-0"
                  title="Supprimer cette thématique"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {topics.length === 0 && (
              <span className="text-[10px] text-slate-500 italic py-1">
                Aucune thématique définie. Le Radar ingérera tous les flux sans filtrage thématique.
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Barre d'action fixe en bas (Sticky footer) */}
      <div className="sticky bottom-0 bg-[#0c0c0e]/90 backdrop-blur-sm pt-2 pb-1 border-t border-white/[0.06] flex justify-end shrink-0 mt-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="px-4 py-1.5 rounded-xl bg-sky-500/20 text-sky-300 border border-sky-500/40 font-medium text-[11px] hover:bg-sky-500/30 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Enregistrement...</span>
            </>
          ) : justSaved ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-300">Enregistré !</span>
            </>
          ) : (
            <>
              <Save className="w-3.5 h-3.5" />
              <span>Sauvegarder</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

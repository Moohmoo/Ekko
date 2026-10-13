import React, { useState, useEffect } from 'react';
import { User, Globe, Tag, Plus, X, Save, Check, Loader2 } from 'lucide-react';
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
  const [userName, setUserName] = useState(userContext?.user_name || '');
  const [language, setLanguage] = useState<'fr' | 'en'>((userContext?.preferred_language as 'fr' | 'en') || 'fr');
  const [preferences, setPreferences] = useState<string[]>(userContext?.preferences || []);
  const [customInstructions, setCustomInstructions] = useState(userContext?.custom_instructions || '');
  const [newTag, setNewTag] = useState('');
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    if (userContext) {
      setUserName(userContext.user_name || '');
      setLanguage((userContext.preferred_language as 'fr' | 'en') || 'fr');
      setPreferences(userContext.preferences || []);
      setCustomInstructions(userContext.custom_instructions || '');
    }
  }, [userContext]);

  const handleAddTag = (e: React.FormEvent) => {
    e.preventDefault();
    const tag = newTag.trim().toLowerCase();
    if (tag && !preferences.includes(tag)) {
      setPreferences([...preferences, tag]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setPreferences(preferences.filter((t) => t !== tagToRemove));
  };

  const handleSave = async () => {
    const success = await onSave({
      user_name: userName.trim() || undefined,
      preferred_language: language,
      preferences,
      custom_instructions: customInstructions.trim() || undefined,
    });
    if (success) {
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    }
  };

  return (
    <div className="flex flex-col gap-3 text-xs select-none">
      {/* Identité & Langue */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2.5">
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <User className="w-4 h-4 text-sky-400" />
          <span>Identité & Préférences Langue</span>
        </div>

        <div className="grid grid-cols-2 gap-2.5 pt-1 border-t border-white/[0.04]">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400">Nom ou pseudonyme</label>
            <input
              type="text"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="Mohamed"
              className="bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/40"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-400 flex items-center gap-1">
              <Globe className="w-3 h-3 text-slate-400" />
              <span>Langue de réponse</span>
            </label>
            <div className="flex bg-black/30 p-0.5 rounded-lg border border-white/[0.06]">
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
      </div>

      {/* Thématiques prioritaires (Tags) */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center justify-between text-slate-200 font-semibold">
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-emerald-400" />
            <span>Thématiques de veille prioritaires</span>
          </div>
          <span className="text-[10px] text-slate-500">{preferences.length} tag(s)</span>
        </div>

        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-white/[0.04]">
          {preferences.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-emerald-950/40 text-emerald-300 border border-emerald-500/30 font-mono"
            >
              <span>#{tag}</span>
              <button
                type="button"
                onClick={() => handleRemoveTag(tag)}
                className="text-emerald-400 hover:text-emerald-200 p-0.5 transition-colors"
                title="Supprimer ce tag"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </span>
          ))}

          {preferences.length === 0 && (
            <span className="text-[10px] text-slate-500 italic">Aucune thématique définie.</span>
          )}
        </div>

        {/* Formulaire ajout rapide de tag */}
        <div className="flex items-center gap-1.5 pt-1">
          <input
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleAddTag(e);
              }
            }}
            placeholder="Nouveau tag (ex: quantum)"
            className="flex-1 bg-black/30 border border-white/[0.06] rounded-lg px-2 py-1 text-[10px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/40"
          />
          <button
            type="button"
            onClick={handleAddTag}
            disabled={!newTag.trim()}
            className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-40"
          >
            <Plus className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Instructions personnalisées */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-1.5">
        <label className="text-slate-200 font-semibold text-[11px]">Instructions personnalisées (Prompt Système)</label>
        <textarea
          rows={2}
          value={customInstructions}
          onChange={(e) => setCustomInstructions(e.target.value)}
          placeholder="Ex: Sois concis et technique, privilégie les sources primaires..."
          className="w-full bg-black/30 border border-white/[0.06] rounded-lg p-2 text-[10px] text-slate-200 placeholder:text-slate-500 resize-none focus:outline-none focus:border-sky-500/40"
        />
      </div>

      {/* Bouton de sauvegarde */}
      <div className="flex justify-end pt-1">
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
              <span>Sauvegarder le profil</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

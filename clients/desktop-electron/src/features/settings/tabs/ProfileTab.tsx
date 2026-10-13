import React, { useState, useEffect } from 'react';
import { User, Globe, ListFilter, Plus, Trash2, Save, Check, Loader2 } from 'lucide-react';
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
  const [newDirective, setNewDirective] = useState('');
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    if (userContext) {
      setUserName(userContext.user_name || '');
      setLanguage((userContext.preferred_language as 'fr' | 'en') || 'fr');
      setPreferences(userContext.preferences || []);
      setCustomInstructions(userContext.custom_instructions || '');
    }
  }, [userContext]);

  const handleAddDirective = (e: React.FormEvent) => {
    e.preventDefault();
    const directive = newDirective.trim();
    if (directive && !preferences.includes(directive)) {
      setPreferences([...preferences, directive]);
      setNewDirective('');
    }
  };

  const handleRemoveDirective = (directiveToRemove: string) => {
    setPreferences(preferences.filter((d) => d !== directiveToRemove));
  };

  const handleSave = async () => {
    const success = await onSave({
      user_name: userName.trim() || null,
      preferred_language: language,
      preferences,
      custom_instructions: customInstructions.trim() || null,
    });
    if (success) {
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    }
  };

  return (
    <div className="relative flex flex-col select-none text-xs pb-16">
      <div className="flex flex-col gap-2.5">
        {/* Identité & Langue */}
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
          <div className="flex items-center gap-2 text-slate-200 font-semibold">
            <User className="w-4 h-4 text-sky-400" />
            <span>Identité & Langue de Synthèse</span>
          </div>

          <div className="grid grid-cols-2 gap-2.5 pt-1 border-t border-white/[0.04]">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-400">Nom / Pseudo</label>
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

        {/* Directives de veille & Thématiques prioritaires */}
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-2">
          <div className="flex items-center justify-between text-slate-200 font-semibold">
            <div className="flex items-center gap-2">
              <ListFilter className="w-4 h-4 text-emerald-400" />
              <span>Directives & Thématiques Prioritaires</span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">{preferences.length} active(s)</span>
          </div>

          {/* Formulaire ajout direct d'une consigne */}
          <form onSubmit={handleAddDirective} className="flex items-center gap-1.5 pt-1 border-t border-white/[0.04]">
            <input
              type="text"
              value={newDirective}
              onChange={(e) => setNewDirective(e.target.value)}
              placeholder="Ex: Architectures de modèles de fondation et raisonnement..."
              className="flex-1 bg-black/30 border border-white/[0.06] rounded-lg px-2.5 py-1.5 text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500/40"
            />
            <button
              type="submit"
              disabled={!newDirective.trim()}
              className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-40 flex items-center gap-1 text-[11px]"
              title="Ajouter la directive"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Ajouter</span>
            </button>
          </form>

          {/* Liste des directives en cartes verticales */}
          <div className="flex flex-col gap-1.5 pt-1">
            {preferences.map((directive, index) => (
              <div
                key={`${directive}-${index}`}
                className="bg-white/[0.02] border border-white/[0.05] rounded-md p-2 text-xs flex justify-between items-start gap-2 hover:border-white/[0.1] transition-colors"
              >
                <span className="text-zinc-300 break-words leading-relaxed text-[11px] flex-1">
                  {directive}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemoveDirective(directive)}
                  className="text-slate-500 hover:text-rose-400 p-0.5 transition-colors shrink-0"
                  title="Supprimer cette directive"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {preferences.length === 0 && (
              <span className="text-[10px] text-slate-500 italic py-1">
                Aucune directive prioritaire définie.
              </span>
            )}
          </div>
        </div>

        {/* Instructions personnalisées (Prompt Système) */}
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-col gap-1.5">
          <label className="text-slate-200 font-semibold text-[11px]">
            Instructions Personnalisées de l'Agent
          </label>
          <textarea
            rows={2}
            value={customInstructions}
            onChange={(e) => setCustomInstructions(e.target.value)}
            placeholder="Ex: Sois concis et technique, privilégie les sources primaires..."
            className="w-full bg-black/30 border border-white/[0.06] rounded-lg p-2 text-[10px] text-slate-200 placeholder:text-slate-500 resize-none focus:outline-none focus:border-sky-500/40"
          />
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
              <span>Sauvegarder le profil</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

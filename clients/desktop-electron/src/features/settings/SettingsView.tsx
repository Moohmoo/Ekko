import React, { useState, useEffect } from 'react';
import { Cpu, Radio, User, Server, AlertCircle, Loader2 } from 'lucide-react';
import { useSettingsStore } from '../../core/stores/useSettingsStore';
import { useDaemonStore } from '../../core/stores/useDaemonStore';
import { ModelsTab } from './tabs/ModelsTab';
import { SourcesTab } from './tabs/SourcesTab';
import { ProfileTab } from './tabs/ProfileTab';
import { SystemTab } from './tabs/SystemTab';

type SettingsTab = 'models' | 'sources' | 'profile' | 'system';

const formatErrorMessage = (rawError: string | null): string => {
  if (!rawError) return '';
  const lower = rawError.toLowerCase();
  if (
    lower.includes('daemon_offline') ||
    lower.includes('econnrefused') ||
    lower.includes('enoent') ||
    lower.includes('socket') ||
    lower.includes('offline')
  ) {
    return "Le daemon Ekko est arrêté. Lancez 'uv run ekko daemon' pour rétablir la liaison IPC.";
  }
  return rawError;
};

export const SettingsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('models');

  const {
    settings,
    userContext,
    sources,
    system,
    isLoading,
    isSaving,
    error,
    fetchSettings,
    saveUserContext,
    toggleSource,
    addRssSource,
    removeSource,
  } = useSettingsStore();

  const isDaemonOnline = useDaemonStore((state) => state.isOnline);

  useEffect(() => {
    if (!settings && !isLoading) {
      fetchSettings();
    }
  }, [settings, isLoading, fetchSettings]);

  const tabs: { id: SettingsTab; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'models', label: 'Modèles & Clés', icon: Cpu },
    { id: 'sources', label: 'Veilleurs', icon: Radio },
    { id: 'profile', label: 'Profil & IA', icon: User },
    { id: 'system', label: 'Système', icon: Server },
  ];

  const userFacingError = formatErrorMessage(error);

  return (
    <div className="flex-1 p-3 flex flex-col h-full overflow-hidden select-none">
      {/* Barre de navigation supérieure (Segmented Control) */}
      <div className="p-1 bg-white/[0.04] rounded-lg border border-white/[0.06] flex gap-1 mb-2.5 text-xs shrink-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-1 px-2 rounded-md flex items-center justify-center gap-1.5 transition-all text-[11px] ${
                isActive
                  ? 'bg-white/[0.1] text-white shadow-sm font-medium'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-400' : 'text-zinc-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Bandeau d'erreur normalisé */}
      {userFacingError && (
        <div className="mb-2 p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px] flex items-center gap-2 shrink-0">
          <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
          <span className="truncate flex-1">{userFacingError}</span>
        </div>
      )}

      {/* Zone de contenu défilante confinée */}
      <div className="flex-1 overflow-y-auto pr-1">
        {isLoading && !settings ? (
          <div className="flex flex-col items-center justify-center h-32 text-slate-400 gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-sky-400" />
            <span className="text-[11px]">Chargement des réglages...</span>
          </div>
        ) : (
          <>
            {activeTab === 'models' && <ModelsTab system={system} />}
            {activeTab === 'sources' && (
              <SourcesTab
                sources={sources}
                isSaving={isSaving}
                onToggleSource={toggleSource}
                onAddRssSource={addRssSource}
                onRemoveSource={removeSource}
              />
            )}
            {activeTab === 'profile' && (
              <ProfileTab
                userContext={userContext}
                isSaving={isSaving}
                onSave={saveUserContext}
              />
            )}
            {activeTab === 'system' && (
              <SystemTab
                system={system}
                isOnline={isDaemonOnline}
                isLoading={isLoading}
                onRefresh={fetchSettings}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

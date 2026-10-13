import { create } from 'zustand';
import type {
  SystemSettings,
  UserContextConfig,
  SourceItem,
  SystemMetadata,
} from '../types';

interface SettingsState {
  settings: SystemSettings | null;
  userContext: UserContextConfig | null;
  sources: SourceItem[];
  system: SystemMetadata | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;

  // Actions
  fetchSettings: () => Promise<void>;
  saveUserContext: (newContext: Partial<UserContextConfig>) => Promise<boolean>;
  toggleSource: (sourceId: string) => Promise<boolean>;
  addRssSource: (id: string, url: string, interval?: string) => Promise<boolean>;
  removeSource: (sourceId: string) => Promise<boolean>;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: null,
  userContext: null,
  sources: [],
  system: null,
  isLoading: false,
  isSaving: false,
  error: null,

  fetchSettings: async () => {
    if (!window.ekkoAPI?.getSystemSettings) {
      set({ error: 'IPC API getSystemSettings non disponible.' });
      return;
    }

    set({ isLoading: true, error: null });
    try {
      const res = await window.ekkoAPI.getSystemSettings();
      if (res) {
        const rawSources = res.sources?.sources || (Array.isArray(res.sources) ? res.sources : []);
        set({
          settings: res,
          userContext: res.user_context || null,
          sources: rawSources,
          system: res.system || null,
          error: null,
        });
      }
    } catch (err: unknown) {
      const msg = (err as Error)?.message || 'Échec de récupération des réglages';
      console.error('[SettingsStore] fetchSettings failed:', msg);
      set({ error: msg });
    } finally {
      set({ isLoading: false });
    }
  },

  saveUserContext: async (newContext: Partial<UserContextConfig>) => {
    if (!window.ekkoAPI?.updateUserContext) {
      set({ error: 'IPC API updateUserContext non disponible.' });
      return false;
    }

    set({ isSaving: true, error: null });
    try {
      const current = get().userContext || {
        preferred_language: 'fr',
        preferences: [],
      };
      const merged: UserContextConfig = {
        ...current,
        ...newContext,
        preferences: newContext.preferences !== undefined ? newContext.preferences : current.preferences,
      };

      const res = await window.ekkoAPI.updateUserContext(merged);
      if (res?.user_context) {
        set((state) => ({
          userContext: res.user_context,
          settings: state.settings
            ? { ...state.settings, user_context: res.user_context }
            : null,
          error: null,
        }));
        return true;
      }
      return false;
    } catch (err: unknown) {
      const msg = (err as Error)?.message || 'Échec de sauvegarde du profil utilisateur';
      console.error('[SettingsStore] saveUserContext failed:', msg);
      set({ error: msg });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },

  toggleSource: async (sourceId: string) => {
    if (!window.ekkoAPI?.updateSources) {
      set({ error: 'IPC API updateSources non disponible.' });
      return false;
    }

    set({ isSaving: true, error: null });
    try {
      const currentSources = get().sources;
      const updatedSources = currentSources.map((s) => {
        if (s.id === sourceId) {
          // If enabled is undefined, default was true, so toggle to false
          const isCurrentlyEnabled = s.enabled !== false;
          return { ...s, enabled: !isCurrentlyEnabled };
        }
        return s;
      });

      const res = await window.ekkoAPI.updateSources(updatedSources);
      const reloadedSources = res?.sources?.sources || updatedSources;
      set((state) => ({
        sources: reloadedSources,
        settings: state.settings
          ? { ...state.settings, sources: { sources: reloadedSources } }
          : null,
        error: null,
      }));
      return true;
    } catch (err: unknown) {
      const msg = (err as Error)?.message || 'Échec de mise à jour des sources';
      console.error('[SettingsStore] toggleSource failed:', msg);
      set({ error: msg });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },

  addRssSource: async (id: string, url: string, interval: string = '1h') => {
    if (!window.ekkoAPI?.updateSources) {
      set({ error: 'IPC API updateSources non disponible.' });
      return false;
    }

    const cleanId = id.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');
    const cleanUrl = url.trim();
    if (!cleanId || !cleanUrl) {
      set({ error: 'ID et URL requis pour ajouter un flux.' });
      return false;
    }

    set({ isSaving: true, error: null });
    try {
      const currentSources = get().sources;
      if (currentSources.some((s) => s.id === cleanId)) {
        set({ error: `Une source avec l'identifiant '${cleanId}' existe déjà.` });
        return false;
      }

      const newSource: SourceItem = {
        id: cleanId,
        type: 'rss',
        url: cleanUrl,
        interval,
        max_items: 20,
        enabled: true,
      };

      const updatedSources = [...currentSources, newSource];
      const res = await window.ekkoAPI.updateSources(updatedSources);
      const reloadedSources = res?.sources?.sources || updatedSources;
      set((state) => ({
        sources: reloadedSources,
        settings: state.settings
          ? { ...state.settings, sources: { sources: reloadedSources } }
          : null,
        error: null,
      }));
      return true;
    } catch (err: unknown) {
      const msg = (err as Error)?.message || "Échec d'ajout de la source RSS";
      console.error('[SettingsStore] addRssSource failed:', msg);
      set({ error: msg });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },

  removeSource: async (sourceId: string) => {
    if (!window.ekkoAPI?.updateSources) {
      set({ error: 'IPC API updateSources non disponible.' });
      return false;
    }

    set({ isSaving: true, error: null });
    try {
      const currentSources = get().sources;
      const updatedSources = currentSources.filter((s) => s.id !== sourceId);

      const res = await window.ekkoAPI.updateSources(updatedSources);
      const reloadedSources = res?.sources?.sources || updatedSources;
      set((state) => ({
        sources: reloadedSources,
        settings: state.settings
          ? { ...state.settings, sources: { sources: reloadedSources } }
          : null,
        error: null,
      }));
      return true;
    } catch (err: unknown) {
      const msg = (err as Error)?.message || 'Échec de suppression de la source';
      console.error('[SettingsStore] removeSource failed:', msg);
      set({ error: msg });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },
}));

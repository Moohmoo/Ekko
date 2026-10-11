import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { NoteItem, ChatMessage } from './core/types';
import { useDaemonHeartbeat } from './core/hooks/useDaemonHeartbeat';
import { useViewStore } from './core/stores/useViewStore';
import { PodHeader } from './components/PodHeader';
import { WelcomeView } from './features/welcome/WelcomeView';
import { HomeView } from './features/home/HomeView';
import { ChatView } from './features/assistant/ChatView';
import { EchoView } from './features/echo/EchoView';
import { SettingsView } from './features/settings/SettingsView';
import { SPRING_SNAPPY, SPRING_BOUNCY } from './design-system/tokens';

export const App: React.FC = () => {
  // Mount 2s polling heartbeat from Zustand store
  useDaemonHeartbeat();

  const { viewMode, setViewMode } = useViewStore();

  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [isLoadingNotes, setIsLoadingNotes] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch Notes on demand
  const fetchNotes = useCallback(async () => {
    if (!window.ekkoAPI) return;
    setIsLoadingNotes(true);
    try {
      const raw = await window.ekkoAPI.getNotes();
      const mapped: NoteItem[] = (raw as Record<string, unknown>[]).map((item) => ({
        id: String(item.id || ''),
        title: String(item.title || 'Signal brut'),
        summary: String(item.clean_content || ''),
        source: String(item.source_id || 'ekko'),
        tags: [String(item.source_id || 'inbox')],
      }));
      setNotes(mapped);
    } catch (e) {
      console.warn('[Frontend] Failed fetching notes:', e);
    } finally {
      setIsLoadingNotes(false);
    }
  }, []);

  // Handle Send Message
  const handleSendMessage = async (text: string) => {
    if (!window.ekkoAPI) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setErrorMessage(null);

    const assistantMsgId = `bot-${Date.now()}`;
    let accumulated = '';

    const cleanup = window.ekkoAPI.onPromptChunk((chunk) => {
      accumulated += chunk;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.id === assistantMsgId) {
          return [...prev.slice(0, -1), { ...last, content: accumulated }];
        } else {
          return [
            ...prev,
            {
              id: assistantMsgId,
              sender: 'ekko',
              content: accumulated,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ];
        }
      });
    });

    try {
      const fullResponse = await window.ekkoAPI.submitPrompt(text);
      setIsStreaming(false);
      cleanup();
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.id === assistantMsgId) {
          return [...prev.slice(0, -1), { ...last, content: fullResponse }];
        } else {
          return [
            ...prev,
            {
              id: assistantMsgId,
              sender: 'ekko',
              content: fullResponse,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ];
        }
      });
    } catch (e: unknown) {
      cleanup();
      setIsStreaming(false);
      setErrorMessage((e as Error).message || 'Erreur lors de la réponse.');
    }
  };


  const handleClose = () => {
    window.ekkoAPI?.closeWindow();
  };

  const isCompact = viewMode === 'welcome' || viewMode === 'home';

  return (
    <motion.div
      initial={{ y: -30, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={SPRING_BOUNCY}
      className={`w-[620px] ${
        isCompact ? 'h-[230px]' : 'h-[460px]'
      } rounded-t-none rounded-b-[26px] bg-[#0c0c0e] border-x border-b border-white/[0.08] border-t-0 shadow-2xl flex flex-col p-3 text-slate-100 transition-[height] duration-300 select-none overflow-hidden`}
    >
      <PodHeader
        activeTab={viewMode}
        onSelectTab={(tab) => {
          setViewMode(tab);
          if (tab === 'echo') fetchNotes();
        }}
        onClose={handleClose}
      />

      <div className="flex-1 flex flex-col mt-2 overflow-hidden">
        <AnimatePresence mode="wait">
          {viewMode === 'welcome' && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={SPRING_SNAPPY}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <WelcomeView />
            </motion.div>
          )}

          {viewMode === 'home' && (
            <motion.div
              key="home"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={SPRING_SNAPPY}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <HomeView />
            </motion.div>
          )}

          {viewMode === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={SPRING_SNAPPY}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <ChatView
                messages={messages}
                onSendMessage={handleSendMessage}
                isStreaming={isStreaming}
                errorMessage={errorMessage}
              />
            </motion.div>
          )}

          {viewMode === 'echo' && (
            <motion.div
              key="echo"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={SPRING_SNAPPY}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <EchoView notes={notes} onRefresh={fetchNotes} isLoading={isLoadingNotes} />
            </motion.div>
          )}

          {viewMode === 'settings' && (
            <motion.div
              key="settings"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={SPRING_SNAPPY}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <SettingsView />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default App;


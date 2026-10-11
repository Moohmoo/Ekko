import React, { useState, useCallback } from 'react';
import type { PodTab, NoteItem, ChatMessage } from './core/types';
import { useDaemonHeartbeat } from './core/hooks/useDaemonHeartbeat';
import { PodHeader } from './components/PodHeader';
import { HomeView } from './features/home/HomeView';
import { ChatView } from './features/assistant/ChatView';
import { EchoView } from './features/echo/EchoView';

export const App: React.FC = () => {
  // Mount 2s polling heartbeat from Zustand store
  useDaemonHeartbeat();

  const [activeTab, setActiveTab] = useState<PodTab>('home');
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

  // Handle File Drop
  const handleFileDrop = async (filePath: string) => {
    setActiveTab('chat');
    await handleSendMessage(`Analyse et indexe ce document déposé : ${filePath}`);
  };

  const handleClose = () => {
    window.ekkoAPI?.closeWindow();
  };

  return (
    <div className="w-[440px] h-[560px] rounded-[28px] bg-[#0c0c0e] border border-white/10 shadow-2xl flex flex-col overflow-hidden text-slate-100">
      <PodHeader
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (tab === 'echo') fetchNotes();
        }}
        onClose={handleClose}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'home' && <HomeView onFileDrop={handleFileDrop} />}
        {activeTab === 'chat' && (
          <ChatView
            messages={messages}
            onSendMessage={handleSendMessage}
            isStreaming={isStreaming}
            errorMessage={errorMessage}
          />
        )}
        {activeTab === 'echo' && (
          <EchoView notes={notes} onRefresh={fetchNotes} isLoading={isLoadingNotes} />
        )}
      </div>
    </div>
  );
};

export default App;

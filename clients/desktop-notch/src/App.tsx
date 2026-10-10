import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { MascotState, PodTab, DistilledNote, ChatMessage, BYOMProfile, DaemonStatus } from './types';
import { PodHeader } from './components/pod/PodHeader';
import { HomeView } from './components/pod/HomeView';
import { ChatView } from './components/pod/ChatView';
import { EchoView } from './components/pod/EchoView';
import { SettingsView } from './components/pod/SettingsView';
import {
  checkDaemonStatus,
  submitPromptToDaemon,
  getDaemonNotes,
  ingestFilePath,
  hideWindow,
} from './services/tauri';

// Synthesizer Web Audio API helper
function playAudioChime(type: 'plop' | 'alert', muted: boolean): void {
  if (muted) return;
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    if (type === 'plop') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(520, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(260, ctx.currentTime + 0.14);
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.16);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.16);
    } else if (type === 'alert') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.2);
    }
  } catch {
    // Ignore audio errors if blocked
  }
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PodTab>('home');
  const [mascotState, setMascotState] = useState<MascotState>('idle');
  const [currentProfile, setCurrentProfile] = useState<BYOMProfile>('micro');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isLoadingNotes, setIsLoadingNotes] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [homeError, setHomeError] = useState<string | null>(null);

  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus>({
    connected: false,
    niceness: 'nice +10',
    vramUsageMb: 0,
    socketPath: '/tmp/ekko.sock',
    activeSources: 6,
  });

  const [notes, setNotes] = useState<DistilledNote[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Real daemon health check
  const handleCheckDaemon = useCallback(async () => {
    const isOnline = await checkDaemonStatus();
    setDaemonStatus((prev) => ({
      ...prev,
      connected: isOnline,
    }));
    return isOnline;
  }, []);

  // Fetch real notes from daemon
  const handleFetchNotes = useCallback(async () => {
    setIsLoadingNotes(true);
    try {
      const realNotes = await getDaemonNotes();
      setNotes(realNotes);
    } catch (e) {
      console.warn('Failed fetching daemon notes:', e);
    } finally {
      setIsLoadingNotes(false);
    }
  }, []);

  // On mount: check daemon and load initial data
  useEffect(() => {
    handleCheckDaemon().then((isOnline) => {
      if (isOnline) {
        handleFetchNotes();
        setMessages([
          {
            id: 'msg-init',
            sender: 'ekko',
            content: 'Bonjour ! Je suis connecté au daemon local. Que souhaites-tu explorer ou analyser ?',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      } else {
        setMessages([
          {
            id: 'msg-offline',
            sender: 'ekko',
            content: '⚠️ Daemon hors ligne. Pour connecter Ekko, lancez dans un terminal :\n`uv run ekko daemon`',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    });
  }, [handleCheckDaemon, handleFetchNotes]);

  // Mascot poke interaction
  const handleMascotClick = useCallback(() => {
    playAudioChime('plop', audioMuted);
    setMascotState((prev) => (prev === 'idle' ? 'dizzy' : 'idle'));
    setTimeout(() => setMascotState('idle'), 2000);
  }, [audioMuted]);

  // Real Drop & Forget action
  const handleDropPayload = useCallback(async (payload: string) => {
    playAudioChime('plop', audioMuted);
    setMascotState('ingestion');
    setHomeError(null);

    try {
      await ingestFilePath(payload);
      setMascotState('alert');
      playAudioChime('alert', audioMuted);
      await handleFetchNotes();
      setTimeout(() => setMascotState('idle'), 1600);
    } catch {
      setHomeError('Daemon hors ligne. Lancez `uv run ekko daemon`.');
      setMascotState('dizzy');
      setTimeout(() => setMascotState('idle'), 2000);
    }
  }, [audioMuted, handleFetchNotes]);

  // Real submit prompt in ChatView
  const handleSendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setChatError(null);
    setMascotState('investigation');

    try {
      const response = await submitPromptToDaemon(text);
      setIsStreaming(false);
      setMascotState('idle');

      const botMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: 'ekko',
        content: response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
      playAudioChime('alert', audioMuted);
    } catch {
      setIsStreaming(false);
      setMascotState('dizzy');
      setChatError('Daemon hors ligne. Lancez `uv run ekko daemon`.');
      setTimeout(() => setMascotState('idle'), 2000);
    }
  }, [audioMuted]);

  // Copy note as Markdown
  const handleCopyNote = useCallback((note: DistilledNote) => {
    const markdown = `# ${note.title}\n\n${note.summary}\n\nTags: ${note.tags.map((t) => `#${t}`).join(' ')}\nSource: ${note.source}\n`;
    navigator.clipboard?.writeText(markdown);
  }, []);

  const springTabTransition = {
    type: 'spring' as const,
    stiffness: 350,
    damping: 26,
  };

  return (
    <div className="w-full h-full min-h-screen flex items-center justify-center bg-transparent p-0 m-0 overflow-hidden select-none">
      {/* Centered Fixed Pod Container (420x540px Style Coucou) */}
      <main className="w-[420px] h-[540px] rounded-[28px] bg-[#0c0c0e]/95 backdrop-blur-2xl border border-white/10 shadow-[0_25px_60px_rgba(0,0,0,0.9)] flex flex-col overflow-hidden text-slate-100">
        {/* Minimalist 44px Icon Header */}
        <PodHeader
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          onClose={() => hideWindow()}
          audioMuted={audioMuted}
          onToggleAudio={() => setAudioMuted(!audioMuted)}
          daemonConnected={daemonStatus.connected}
        />

        {/* Pod Body with Fluid Spring Tab Switching */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <AnimatePresence mode="wait">
            {activeTab === 'home' && (
              <motion.div
                key="tab-home"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={springTabTransition}
                className="flex-1 flex flex-col overflow-hidden h-full"
              >
                <HomeView
                  mascotState={mascotState}
                  onMascotClick={handleMascotClick}
                  onDropPayload={handleDropPayload}
                  telemetry={{
                    niceness: daemonStatus.niceness,
                    vramUsageMb: daemonStatus.vramUsageMb,
                    isOnline: daemonStatus.connected,
                  }}
                  errorMessage={homeError}
                />
              </motion.div>
            )}

            {activeTab === 'chat' && (
              <motion.div
                key="tab-chat"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={springTabTransition}
                className="flex-1 flex flex-col overflow-hidden h-full"
              >
                <ChatView
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isStreaming={isStreaming}
                  currentProfile={currentProfile}
                  daemonConnected={daemonStatus.connected}
                  errorMessage={chatError}
                />
              </motion.div>
            )}

            {activeTab === 'echo' && (
              <motion.div
                key="tab-echo"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={springTabTransition}
                className="flex-1 flex flex-col overflow-hidden h-full"
              >
                <EchoView
                  notes={notes}
                  onCopyNote={handleCopyNote}
                  onRefreshNotes={handleFetchNotes}
                  isLoading={isLoadingNotes}
                />
              </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div
                key="tab-settings"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={springTabTransition}
                className="flex-1 flex flex-col overflow-hidden h-full"
              >
                <SettingsView
                  currentProfile={currentProfile}
                  onSelectProfile={setCurrentProfile}
                  daemonStatus={daemonStatus}
                  onTestPing={async () => {
                    await handleCheckDaemon();
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default App;

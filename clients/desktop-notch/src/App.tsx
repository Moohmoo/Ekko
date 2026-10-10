import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { MascotState, PodTab, DistilledNote, ChatMessage, BYOMProfile, DaemonStatus } from './types';
import { PodHeader } from './components/pod/PodHeader';
import { HomeView } from './components/pod/HomeView';
import { ChatView } from './components/pod/ChatView';
import { EchoView } from './components/pod/EchoView';
import { SettingsView } from './components/pod/SettingsView';
import {
  hideWindow,
  pingDaemon,
  submitPrompt,
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
    // Ignore audio errors if audio context blocked by browser policy
  }
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PodTab>('home');
  const [mascotState, setMascotState] = useState<MascotState>('idle');
  const [currentProfile, setCurrentProfile] = useState<BYOMProfile>('micro');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [audioMuted, setAudioMuted] = useState<boolean>(false);

  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus>({
    connected: true,
    niceness: 'nice +10',
    vramUsageMb: 0,
    socketPath: '/tmp/ekko.sock',
    activeSources: 6,
  });

  const [notes, setNotes] = useState<DistilledNote[]>([
    {
      id: 'note-1',
      title: 'Attention Decay & Context Compression in Agentic LLMs',
      summary:
        'Synthèse Map-Reduce : réduction de 70% de la VRAM requise sans perte d’évocation sur contextes 128k.',
      tags: ['ai-arch', 'compression', 'arxiv'],
      source: 'arXiv · 2409.Attention',
      sourceType: 'arxiv',
      createdAt: '12m',
      obsidianSaved: true,
    },
    {
      id: 'note-2',
      title: 'Rust vs Tauri v2 IPC Throughput & Memory Bounds',
      summary:
        'Benchmarks de bande passante sur socket UNIX. Élimination du surcoût JSON pour les flux volumineux.',
      tags: ['tauri', 'rust-ipc'],
      source: 'Drop · Benchmarks.md',
      sourceType: 'drop',
      createdAt: 'Hier',
      obsidianSaved: true,
    },
  ]);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-init',
      sender: 'ekko',
      content:
        'Bonjour ! Je veille sur tes 6 flux déclarés. 2 ruptures ont été consolidées aujourd’hui. Que souhaites-tu explorer ?',
      timestamp: 'Maintenant',
    },
  ]);

  // Mascot poke interaction
  const handleMascotClick = useCallback(() => {
    playAudioChime('plop', audioMuted);
    setMascotState((prev) => (prev === 'idle' ? 'dizzy' : 'idle'));
    setTimeout(() => setMascotState('idle'), 2000);
  }, [audioMuted]);

  // Drop & Forget action
  const handleDropPayload = useCallback((payload: string) => {
    playAudioChime('plop', audioMuted);
    setMascotState('ingestion');

    setTimeout(() => {
      const newNote: DistilledNote = {
        id: `note-${Date.now()}`,
        title: payload.startsWith('http') ? `Ingestion Web: ${payload}` : `Document: ${payload}`,
        summary:
          'Signal absorbé et distillé en tâche de fond par le pipeline local. Fiche Markdown générée dans Obsidian.',
        tags: ['ingestion', 'drop-and-forget'],
        source: 'Drop & Forget',
        sourceType: 'drop',
        createdAt: 'À l’instant',
        obsidianSaved: true,
      };

      setNotes((prev) => [newNote, ...prev]);
      setMascotState('alert');
      playAudioChime('alert', audioMuted);

      setTimeout(() => {
        setMascotState('idle');
      }, 1600);
    }, 1200);
  }, [audioMuted]);

  // Submit prompt in ChatView
  const handleSendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setMascotState('investigation');

    await submitPrompt(text);

    setTimeout(() => {
      setIsStreaming(false);
      setMascotState('idle');
      const botMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: 'ekko',
        content: `D’après ma mémoire hybride (SQLite-vec + FTS5), voici les points saillants concernant "${text}" :\n\n• Fiche Obsidian synchronisée dans le PKM local.\n• Confinement matériel respecté : 0 Mo VRAM résiduelle.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
      playAudioChime('alert', audioMuted);
    }, 1600);
  }, [audioMuted]);

  // Copy note as Markdown
  const handleCopyNote = useCallback((note: DistilledNote) => {
    const markdown = `# ${note.title}\n\n${note.summary}\n\nTags: ${note.tags.map((t) => `#${t}`).join(' ')}\nSource: ${note.source}\n`;
    navigator.clipboard?.writeText(markdown);
  }, []);

  // Ping daemon
  const handleTestPing = useCallback(async () => {
    const res = await pingDaemon();
    setDaemonStatus((prev) => ({
      ...prev,
      connected: res.status === 'ok',
    }));
  }, []);

  // Periodic daemon check
  useEffect(() => {
    handleTestPing();
  }, [handleTestPing]);

  const springTabTransition = {
    type: 'spring' as const,
    stiffness: 350,
    damping: 26,
  };

  return (
    <div className="w-full h-full min-h-screen flex items-center justify-center bg-transparent p-0 m-0 overflow-hidden select-none">
      {/* Centered Fixed Pod Container (440x560px Style Coucou) */}
      <main className="w-[440px] h-[560px] rounded-[28px] bg-[#0c0c0e]/95 backdrop-blur-2xl border border-white/10 shadow-[0_25px_60px_rgba(0,0,0,0.9)] flex flex-col overflow-hidden text-slate-100">
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
                className="flex-1 flex flex-col overflow-hidden"
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
                className="flex-1 flex flex-col overflow-hidden"
              >
                <ChatView
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isStreaming={isStreaming}
                  currentProfile={currentProfile}
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
                className="flex-1 flex flex-col overflow-hidden"
              >
                <EchoView notes={notes} onCopyNote={handleCopyNote} />
              </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div
                key="tab-settings"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={springTabTransition}
                className="flex-1 flex flex-col overflow-hidden"
              >
                <SettingsView
                  currentProfile={currentProfile}
                  onSelectProfile={setCurrentProfile}
                  daemonStatus={daemonStatus}
                  onTestPing={handleTestPing}
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

import React, { useState, useEffect, useCallback } from 'react';
import type { MascotState, TabType, DistilledNote, ChatMessage, BYOMProfile, DaemonStatus } from './types';
import { NotchHeader } from './components/notch/NotchHeader';
import { NotchDrawer } from './components/drawer/NotchDrawer';
import {
  setNotchExpanded,
  pingDaemon,
  submitPrompt,
} from './services/tauri';

// Synthesizer Web Audio API helper for zero-dependency micro-interactions
function playAudioChime(type: 'plop' | 'alert' | 'complete'): void {
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
    // Graceful fallback if audio is not allowed or unsupported
  }
}

export const App: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [mascotState, setMascotState] = useState<MascotState>('idle');
  const [activeTab, setActiveTab] = useState<TabType>('echo');
  const [currentProfile, setCurrentProfile] = useState<BYOMProfile>('standard');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

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
        'Bonjour ! Je veille sur tes flux configurés et ta mémoire PKM. Que souhaites-tu explorer ?',
      timestamp: 'Maintenant',
    },
  ]);

  // Sync window size with Tauri when expansion changes
  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => {
      const next = !prev;
      setNotchExpanded(next);
      setMascotState(next ? 'drawer' : 'idle');
      return next;
    });
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setIsExpanded(false);
    setNotchExpanded(false);
    setMascotState('idle');
  }, []);

  // Handle dropping a document, URL or file on Drop & Forget
  const handleDropPayload = useCallback((payload: string) => {
    playAudioChime('plop');
    setMascotState('ingestion');

    setTimeout(() => {
      const newNote: DistilledNote = {
        id: `note-${Date.now()}`,
        title: payload.startsWith('http') ? `Ingestion Web: ${payload}` : `Fichier: ${payload}`,
        summary:
          'Signal absorbé et distillé en tâche de fond par le pipeline local. Fiche Obsidian générée.',
        tags: ['ingestion', 'drop-and-forget'],
        source: 'Drop & Forget',
        sourceType: 'drop',
        createdAt: 'À l’instant',
        obsidianSaved: true,
      };

      setNotes((prev) => [newNote, ...prev]);
      setMascotState('alert');
      playAudioChime('alert');

      setTimeout(() => {
        setMascotState(isExpanded ? 'drawer' : 'idle');
      }, 1500);
    }, 1200);
  }, [isExpanded]);

  // Handle user submitting message in Assistant tab
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

    // Trigger submit prompt to Tauri / Daemon
    await submitPrompt(text);

    // Simulate response delay or response handling
    setTimeout(() => {
      setIsStreaming(false);
      setMascotState('drawer');
      const botMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        sender: 'ekko',
        content: `D'après ma mémoire hybride (SQLite-vec + FTS5), voici les éléments clés concernant "${text}" :\n\n• Synthèse indexée dans Obsidian : 2 fiches correspondantes trouvées.\n• Confinement matériel respecté : VRAM à 0 Mo déchargée.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
      playAudioChime('alert');
    }, 1800);
  }, []);

  // Copy note as Markdown
  const handleCopyNote = useCallback((note: DistilledNote) => {
    const markdown = `# ${note.title}\n\n${note.summary}\n\nTags: ${note.tags.map((t) => `#${t}`).join(' ')}\nSource: ${note.source}\n`;
    navigator.clipboard?.writeText(markdown);
  }, []);

  // Test Ping daemon
  const handleTestPing = useCallback(async () => {
    const res = await pingDaemon();
    setDaemonStatus((prev) => ({
      ...prev,
      connected: res.status === 'ok',
    }));
  }, []);

  // Periodic daemon health check
  useEffect(() => {
    handleTestPing();
  }, [handleTestPing]);

  return (
    <div className="w-full h-screen p-0 m-0 flex flex-col items-center justify-start overflow-hidden bg-transparent select-none">
      {/* 32px HUD Retracted Header */}
      <NotchHeader
        isExpanded={isExpanded}
        onToggleExpand={handleToggleExpand}
        mascotState={mascotState}
        onDropPayload={handleDropPayload}
        telemetry={{
          niceness: daemonStatus.niceness,
          vramUsageMb: daemonStatus.vramUsageMb,
          isOnline: daemonStatus.connected,
        }}
      />

      {/* 3-Tab Bento Drawer */}
      <NotchDrawer
        isOpen={isExpanded}
        onClose={handleCloseDrawer}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        notes={notes}
        onCopyNote={handleCopyNote}
        messages={messages}
        onSendMessage={handleSendMessage}
        isStreaming={isStreaming}
        currentProfile={currentProfile}
        onSelectProfile={setCurrentProfile}
        daemonStatus={daemonStatus}
        onTestPing={handleTestPing}
      />
    </div>
  );
};

export default App;

import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDaemonHeartbeat } from './core/hooks/useDaemonHeartbeat';
import { useTraySync } from './core/hooks/useTraySync';
import { useBufferStore } from './core/stores/useBufferStore';
import { useViewStore } from './core/stores/useViewStore';
import { PodShell } from './components/PodShell';
import { PodHeader } from './components/PodHeader';
import { WelcomeView } from './features/welcome/WelcomeView';
import { HomeView } from './features/home/HomeView';
import { RadarView } from './features/radar/RadarView';
import { BufferView } from './features/buffer/BufferView';
import { SettingsView } from './features/settings/SettingsView';
import { LAYOUT } from './design-system/tokens';

export const App: React.FC = () => {
  // Mount 2s polling heartbeat from Zustand store
  useDaemonHeartbeat();
  // Synchronize OS System Tray icon with reactive states
  useTraySync();

  const { viewMode, setViewMode } = useViewStore();
  const fetchNotes = useBufferStore((state) => state.fetchNotes);

  const handleClose = () => {
    window.ekkoAPI?.closeWindow();
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        window.ekkoAPI?.closeWindow();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const isCompact = viewMode === 'welcome' || viewMode === 'home' || viewMode === 'radar';
  const targetHeight = isCompact ? LAYOUT.podHeightCompact : LAYOUT.podHeightExtended;

  return (
    <PodShell
      targetHeight={targetHeight}
      header={
        <PodHeader
          activeTab={viewMode}
          onSelectTab={(tab) => {
            setViewMode(tab);
            if (tab === 'buffer' || (tab as string) === 'echo') fetchNotes();
          }}
          onClose={handleClose}
        />
      }
    >
      <AnimatePresence mode="wait">
        {viewMode === 'welcome' && (
          <motion.div
            key="welcome"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute inset-0 w-full h-full flex flex-col overflow-hidden"
          >
            <WelcomeView />
          </motion.div>
        )}

        {viewMode === 'home' && (
          <motion.div
            key="home"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute inset-0 w-full h-full flex flex-col overflow-hidden"
          >
            <HomeView />
          </motion.div>
        )}

        {viewMode === 'radar' && (
          <motion.div
            key="radar"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute inset-0 w-full h-full flex flex-col overflow-hidden"
          >
            <RadarView />
          </motion.div>
        )}

        {(viewMode === 'buffer' || (viewMode as string) === 'echo') && (
          <motion.div
            key="buffer"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute inset-0 w-full h-full flex flex-col overflow-hidden"
          >
            <BufferView />
          </motion.div>
        )}

        {viewMode === 'settings' && (
          <motion.div
            key="settings"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute inset-0 w-full h-full flex flex-col overflow-hidden"
          >
            <SettingsView />
          </motion.div>
        )}
      </AnimatePresence>
    </PodShell>
  );
};

export default App;

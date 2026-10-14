import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDaemonHeartbeat } from './core/hooks/useDaemonHeartbeat';
import { useTraySync } from './core/hooks/useTraySync';
import { useEchoStore } from './core/stores/useEchoStore';
import { useViewStore } from './core/stores/useViewStore';
import { PodHeader } from './components/PodHeader';
import { WelcomeView } from './features/welcome/WelcomeView';
import { HomeView } from './features/home/HomeView';
import { EchoView } from './features/echo/EchoView';
import { SettingsView } from './features/settings/SettingsView';
import { SPRING_SNAPPY, SPRING_BOUNCY, LAYOUT, COLORS, SURFACES } from './design-system/tokens';

export const App: React.FC = () => {
  // Mount 2s polling heartbeat from Zustand store
  useDaemonHeartbeat();
  // Synchronize OS System Tray icon with reactive states
  useTraySync();

  const { viewMode, setViewMode } = useViewStore();
  const { notes, isLoading: isLoadingNotes, fetchNotes } = useEchoStore();

  const handleClose = () => {
    window.ekkoAPI?.closeWindow();
  };

  React.useEffect(() => {
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

  const isCompact = viewMode === 'welcome' || viewMode === 'home';
  const targetHeight = isCompact ? LAYOUT.podHeightCompact : LAYOUT.podHeightExtended;

  return (
    <div className="relative w-[620px] mx-auto select-none pt-0">
      {/* Left concave fillet: seamless organic transition from horizontal GNOME bar to notch vertical flank */}
      <svg
        className="absolute top-0 -left-5 w-[21px] h-5 pointer-events-none select-none z-10"
        viewBox="0 0 21 20"
        fill="none"
        aria-hidden="true"
      >
        <path d="M 0 0 A 20 20 0 0 1 20 20 H 21 V 0 H 0 Z" fill={COLORS.bgOled} />
        <path
          d="M 0 0 A 20 20 0 0 1 20 20"
          stroke={COLORS.borderDefault}
          strokeWidth="1"
          fill="none"
        />
      </svg>

      {/* Right concave fillet: symmetric seamless organic transition to top panel */}
      <svg
        className="absolute top-0 -right-5 w-[21px] h-5 pointer-events-none select-none z-10"
        viewBox="0 0 21 20"
        fill="none"
        aria-hidden="true"
      >
        <path d="M 1 20 A 20 20 0 0 1 21 0 H 0 V 20 H 1 Z" fill={COLORS.bgOled} />
        <path
          d="M 1 20 A 20 20 0 0 1 21 0"
          stroke={COLORS.borderDefault}
          strokeWidth="1"
          fill="none"
        />
      </svg>

      {/* Notch core container: seamless top edge, rounded bottom, spring height morphing */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, height: targetHeight }}
        transition={{
          opacity: SPRING_BOUNCY,
          height: SPRING_SNAPPY,
        }}
        className={`w-full ${SURFACES.shell} rounded-b-[22px] rounded-t-none border-t-0 flex flex-col p-2.5 text-slate-100 overflow-hidden`}
        style={{ borderTop: 'none' }}
      >
        <PodHeader
          activeTab={viewMode}
          onSelectTab={(tab) => {
            setViewMode(tab);
            if (tab === 'echo') fetchNotes();
          }}
          onClose={handleClose}
        />

        {/* Unified Stage: Single inner surface with direct, natural transitions */}
        <div className="flex-1 flex flex-col mt-1.5 rounded-2xl bg-surface border border-white/[0.08] shadow-inner relative overflow-hidden">
          <AnimatePresence>
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


            {viewMode === 'echo' && (
              <motion.div
                key="echo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                className="absolute inset-0 w-full h-full flex flex-col overflow-hidden"
              >
                <EchoView notes={notes} onRefresh={fetchNotes} isLoading={isLoadingNotes} />
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
        </div>
      </motion.div>
    </div>
  );
};

export default App;


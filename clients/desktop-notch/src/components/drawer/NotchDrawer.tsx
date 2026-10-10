import React from 'react';
import { motion, AnimatePresence, type Transition } from 'framer-motion';
import { X, Sparkles, MessageSquare, SlidersHorizontal } from 'lucide-react';
import type { TabType, DistilledNote, ChatMessage, BYOMProfile, DaemonStatus } from '../../types';
import { EchoTab } from './EchoTab';
import { AssistantTab } from './AssistantTab';
import { SettingsTab } from './SettingsTab';

interface NotchDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
  notes: DistilledNote[];
  onCopyNote: (note: DistilledNote) => void;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  isStreaming: boolean;
  currentProfile: BYOMProfile;
  onSelectProfile: (profile: BYOMProfile) => void;
  daemonStatus: DaemonStatus;
  onTestPing: () => Promise<void>;
}

export const NotchDrawer: React.FC<NotchDrawerProps> = ({
  isOpen,
  onClose,
  activeTab,
  onSelectTab,
  notes,
  onCopyNote,
  messages,
  onSendMessage,
  isStreaming,
  currentProfile,
  onSelectProfile,
  daemonStatus,
  onTestPing,
}) => {
  const springTransition: Transition = {
    type: 'spring',
    stiffness: 380,
    damping: 28,
    mass: 0.8,
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'echo', label: 'Écho', icon: <Sparkles className="w-3 h-3" /> },
    { id: 'assistant', label: 'Assistant', icon: <MessageSquare className="w-3 h-3" /> },
    { id: 'settings', label: 'Réglages', icon: <SlidersHorizontal className="w-3 h-3" /> },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="notch-drawer"
          layout
          initial={{ opacity: 0, y: -10, scaleY: 0.95 }}
          animate={{ opacity: 1, y: 0, scaleY: 1 }}
          exit={{ opacity: 0, y: -10, scaleY: 0.95 }}
          transition={springTransition}
          className="glass-drawer w-full rounded-2xl mt-1.5 border border-white/10 overflow-hidden origin-top shadow-2xl flex flex-col"
        >
          {/* Drawer Header with Animated Tab Indicator */}
          <div className="px-3 pt-2.5 pb-2 border-b border-white/10 flex items-center justify-between bg-black/30">
            <div className="flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/5">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => onSelectTab(tab.id)}
                    className={`relative px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
                      isActive ? 'text-cyan-200' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="activeTabPill"
                        className="absolute inset-0 bg-cyan-500/20 border border-cyan-500/30 rounded-lg shadow-sm"
                        transition={springTransition}
                      />
                    )}
                    <span className="relative z-10 flex items-center gap-1.5 text-[11px]">
                      {tab.icon}
                      {tab.label}
                    </span>
                  </button>
                );
              })}
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              title="Fermer le tiroir"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Drawer Body Container */}
          <div className="p-3">
            {activeTab === 'echo' && (
              <EchoTab notes={notes} onCopyNote={onCopyNote} />
            )}
            {activeTab === 'assistant' && (
              <AssistantTab
                messages={messages}
                onSendMessage={onSendMessage}
                isStreaming={isStreaming}
              />
            )}
            {activeTab === 'settings' && (
              <SettingsTab
                currentProfile={currentProfile}
                onSelectProfile={onSelectProfile}
                daemonStatus={daemonStatus}
                onTestPing={onTestPing}
              />
            )}
          </div>

          {/* Drawer Footer with Status Information */}
          <div className="px-3 py-1.5 border-t border-white/5 bg-black/40 flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              Local-first · Zéro Cloud par défaut
            </span>
            <span>Tauri v2 · HUD 32px</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NotchDrawer;

import React, { useState, useEffect, useMemo } from 'react';
import type { NoteItem } from '../../core/types';
import { useBufferStore } from '../../core/stores/useBufferStore';
import { Layers, Copy, Check, Search, X, AlertTriangle, Tag, Sparkles, RotateCw } from 'lucide-react';
import { BufferDetailView } from './BufferDetailView';
import { AnimatePresence, motion } from 'framer-motion';
import { SPRING_SNAPPY } from '../../design-system/tokens';
import { formatSourceDisplay, normalizeTag } from '../../core/utils/formatters';

interface BufferViewProps {
  notes?: NoteItem[];
  onRefresh?: () => void;
  isLoading?: boolean;
}

const SEARCH_DEBOUNCE_MS = 150;

/**
 * BufferView displays the active cognitive buffer:
 * In-transit notes, instant hybrid search, tag filtering, and Obsidian markdown exports.
 */
export const BufferView: React.FC<BufferViewProps> = () => {
  const notes = useBufferStore((state) => state.notes);
  const isManualRefreshing = useBufferStore((state) => state.isManualRefreshing);
  const isOffline = useBufferStore((state) => state.isOffline);
  const selectedTag = useBufferStore((state) => state.selectedTag);
  const searchNotes = useBufferStore((state) => state.searchNotes);
  const filterByTag = useBufferStore((state) => state.filterByTag);
  const refresh = useBufferStore((state) => state.refresh);
  const fetchNotes = useBufferStore((state) => state.fetchNotes);

  const [searchInput, setSearchInput] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<NoteItem | null>(null);

  // Trigger fetchNotes on mount
  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  // Debounce search effect (150 ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      searchNotes(searchInput);
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchInput, searchNotes]);

  // Client-side filtering by selected tag if set
  const displayedNotes = useMemo(() => {
    if (!selectedTag) return notes;
    const lowerTag = normalizeTag(selectedTag);
    return notes.filter((n) =>
      n.tags.some((t) => normalizeTag(t) === lowerTag)
    );
  }, [notes, selectedTag]);

  const handleCopy = (e: React.MouseEvent, note: NoteItem) => {
    e.stopPropagation();
    // Obsidian standard format: ## [[Titre]]\n...
    const md = `## [[${note.title}]]\n\n${note.summary || note.content || ''}\n\n**Source:** ${note.source}\n`;
    navigator.clipboard?.writeText(md);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    searchNotes('');
  };

  const handleClearTag = () => {
    filterByTag(null);
  };

  const isSearchActive = searchInput.trim().length > 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-3 gap-2 select-none relative">
      <AnimatePresence mode="wait" initial={false}>
        {selectedNote ? (
          <BufferDetailView
            key={`detail-${selectedNote.id}`}
            note={selectedNote}
            onBack={() => setSelectedNote(null)}
            onSelectTag={(tag) => filterByTag(tag)}
          />
        ) : (
          <motion.div
            key="list"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            transition={SPRING_SNAPPY}
            className="flex-1 flex flex-col h-full min-h-0 overflow-hidden gap-2"
          >
            {/* Offline Alert Banner */}
            {isOffline && (
              <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] shrink-0">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                <span className="truncate">Daemon disconnected · Offline view (cached data)</span>
              </div>
            )}

            {/* Top Bar: Search Input + Compact Icon Refresh Button */}
            <div className="flex items-center gap-1.5 shrink-0">
              <div className="flex-1 relative flex items-center">
                <Search className="w-3.5 h-3.5 absolute left-2.5 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search notes, ideas..."
                  className="w-full pl-8 pr-7 py-1.5 text-xs bg-white/[0.04] border border-white/[0.08] rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/50 focus:bg-white/[0.06] transition-colors"
                />
                {searchInput && (
                  <button
                    onClick={handleClearSearch}
                    className="absolute right-2 p-0.5 rounded text-slate-400 hover:text-slate-200 transition-colors"
                    title="Clear search"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Compact reload icon button */}
              <button
                onClick={() => refresh()}
                disabled={isManualRefreshing}
                className="w-7 h-7 flex items-center justify-center rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-400 hover:text-sky-300 disabled:opacity-40 transition-colors shrink-0"
                title="Refresh list (preserves active search)"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isManualRefreshing ? 'animate-spin text-sky-400' : ''}`} />
              </button>
            </div>

            {/* Active Filter Bar (Tag / Search count) */}
            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 shrink-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <span>
                  {displayedNotes.length} {displayedNotes.length > 1 ? 'notes' : 'note'}
                </span>
                {isSearchActive && (
                  <span className="flex items-center gap-1 text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded-md border border-sky-500/20">
                    <Sparkles className="w-3 h-3" />
                    <span>hybrid</span>
                  </span>
                )}
                {selectedTag && (
                  <span className="flex items-center gap-1 bg-white/[0.06] border border-white/10 px-2 py-0.5 rounded-md text-slate-200">
                    <Tag className="w-2.5 h-2.5 text-sky-400" />
                    <span>#{selectedTag}</span>
                    <button
                      onClick={handleClearTag}
                      className="hover:text-white transition-colors ml-0.5"
                      title="Clear tag filter"
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  </span>
                )}
              </div>
            </div>

            {/* Notes List or Empty State */}
            <div className="flex-1 overflow-y-auto pr-1 space-y-2 min-h-0">
              {displayedNotes.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center text-slate-500 gap-2 p-4">
                  <Layers className="w-8 h-8 text-slate-600" />
                  <p className="text-xs">
                    {isSearchActive || selectedTag
                      ? 'No notes match your filter'
                      : 'No notes in buffer yet'}
                  </p>
                  {(isSearchActive || selectedTag) && (
                    <button
                      onClick={() => {
                        handleClearSearch();
                        handleClearTag();
                      }}
                      className="text-xs text-sky-400 hover:text-sky-300 transition-colors"
                    >
                      Reset filters
                    </button>
                  )}
                </div>
              ) : (
                displayedNotes.map((note) => {
                  const primarySourceRaw = (note.sources && note.sources[0]) || note.source;
                  const sourceInfo = formatSourceDisplay(primarySourceRaw);

                  return (
                    <div
                      key={note.id}
                      onClick={() => setSelectedNote(note)}
                      className="group p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] hover:border-sky-500/30 transition-all cursor-pointer relative"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-xs font-semibold text-slate-100 group-hover:text-sky-300 transition-colors line-clamp-1 flex-1">
                          {note.title}
                        </h3>

                        {/* Fast copy Obsidian markdown button */}
                        <button
                          onClick={(e) => handleCopy(e, note)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-all shrink-0"
                          title="Copy Obsidian Markdown"
                        >
                          {copiedId === note.id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>

                      {note.summary && (
                        <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-snug">
                          {note.summary}
                        </p>
                      )}

                      <div className="flex items-center gap-2 mt-2 text-[10px] text-slate-500">
                        <span className="truncate max-w-[180px]">
                          {sourceInfo.label}
                        </span>
                        {note.tags && note.tags.length > 0 && (
                          <div className="flex items-center gap-1 overflow-hidden">
                            <span>•</span>
                            <span className="truncate text-slate-400">
                              #{normalizeTag(note.tags[0])}
                            </span>
                            {note.tags.length > 1 && (
                              <span className="text-[9px] text-slate-500">
                                +{note.tags.length - 1}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default BufferView;

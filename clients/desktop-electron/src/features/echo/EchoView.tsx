import React, { useState, useEffect, useMemo } from 'react';
import type { NoteItem } from '../../core/types';
import { useEchoStore } from '../../core/stores/useEchoStore';
import { Layers, Copy, Check, Search, X, AlertTriangle, Tag, Sparkles } from 'lucide-react';
import { NoteDetailModal } from './NoteDetailModal';
import { AnimatePresence } from 'framer-motion';

interface EchoViewProps {
  notes?: NoteItem[];
  onRefresh?: () => void;
  isLoading?: boolean;
}

const SEARCH_DEBOUNCE_MS = 300;

export const EchoView: React.FC<EchoViewProps> = () => {
  const notes = useEchoStore((state) => state.notes);
  const isLoading = useEchoStore((state) => state.isLoading);
  const isOffline = useEchoStore((state) => state.isOffline);
  const selectedTag = useEchoStore((state) => state.selectedTag);
  const fetchNotes = useEchoStore((state) => state.fetchNotes);
  const searchNotes = useEchoStore((state) => state.searchNotes);
  const filterByTag = useEchoStore((state) => state.filterByTag);

  const [searchInput, setSearchInput] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeNote, setActiveNote] = useState<NoteItem | null>(null);

  // Debounce search effect (300 ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      searchNotes(searchInput);
    }, SEARCH_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchInput, searchNotes]);

  // Client-side filtering by selected tag if set
  const displayedNotes = useMemo(() => {
    if (!selectedTag) return notes;
    const lowerTag = selectedTag.toLowerCase();
    return notes.filter((n) =>
      n.tags.some((t) => t.toLowerCase() === lowerTag)
    );
  }, [notes, selectedTag]);

  const handleCopy = (e: React.MouseEvent, note: NoteItem) => {
    e.stopPropagation();
    const md = `# ${note.title}\n\n${note.content || note.summary}\n\nSource: ${note.source}\n`;
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
      {/* Offline Alert Banner */}
      {isOffline && (
        <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] shrink-0">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
          <span className="truncate">Daemon déconnecté · Affichage hors-ligne (données en cache)</span>
        </div>
      )}

      {/* Top Bar: Search Input + Refresh Button */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="flex-1 relative flex items-center">
          <Search className="w-3.5 h-3.5 absolute left-2.5 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Recherche hybride (titre, contenu, sémantique)..."
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-white/[0.04] border border-white/[0.08] rounded-xl text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500/50 focus:bg-white/[0.06] transition-colors"
          />
          {searchInput && (
            <button
              onClick={handleClearSearch}
              className="absolute right-2 p-0.5 rounded text-slate-400 hover:text-slate-200 transition-colors"
              title="Effacer la recherche"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        <button
          onClick={() => fetchNotes()}
          disabled={isLoading}
          className="px-2.5 py-1.5 text-[11px] font-medium text-sky-400 hover:text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-xl disabled:opacity-40 transition-colors shrink-0"
        >
          {isLoading ? 'Sync...' : 'Rafraîchir'}
        </button>
      </div>

      {/* Active Filter Bar (Tag / Search count) */}
      <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span>
            {displayedNotes.length} {displayedNotes.length > 1 ? 'fiches' : 'fiche'}
          </span>
          {isSearchActive && (
            <span className="flex items-center gap-1 text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded-md border border-sky-500/20">
              <Sparkles className="w-3 h-3" />
              <span>hybride</span>
            </span>
          )}
          {selectedTag && (
            <span className="flex items-center gap-1 bg-white/[0.06] border border-white/10 px-2 py-0.5 rounded-md text-slate-200">
              <Tag className="w-2.5 h-2.5 text-sky-400" />
              <span>#{selectedTag}</span>
              <button
                onClick={handleClearTag}
                className="hover:text-rose-400 ml-0.5 transition-colors"
                title="Supprimer le filtre de tag"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
        </div>

        {(isSearchActive || selectedTag) && (
          <button
            onClick={() => {
              handleClearSearch();
              handleClearTag();
            }}
            className="text-[10px] text-slate-500 hover:text-slate-300 underline"
          >
            Réinitialiser
          </button>
        )}
      </div>

      {/* Notes List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs">
        {displayedNotes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2 p-4 text-center">
            <Layers className="w-8 h-8 opacity-40" />
            {isSearchActive ? (
              <div className="space-y-1">
                <p className="text-slate-400">Aucun résultat pour « {searchInput} »</p>
                <button
                  onClick={handleClearSearch}
                  className="text-sky-400 hover:underline text-[11px]"
                >
                  Effacer la recherche
                </button>
              </div>
            ) : selectedTag ? (
              <div className="space-y-1">
                <p className="text-slate-400">Aucune note avec le tag #{selectedTag}</p>
                <button
                  onClick={handleClearTag}
                  className="text-sky-400 hover:underline text-[11px]"
                >
                  Afficher toutes les notes
                </button>
              </div>
            ) : (
              <span>Aucune note dans le tampon cognitif.</span>
            )}
          </div>
        ) : (
          displayedNotes.map((note) => (
            <div
              key={note.id}
              onClick={() => setActiveNote(note)}
              className="p-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-sky-500/30 hover:bg-white/[0.05] transition-all cursor-pointer flex flex-col gap-1.5 group"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-semibold text-slate-100 text-[11px] line-clamp-1 group-hover:text-sky-200 transition-colors">
                  {note.title}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {note.score !== undefined && (
                    <span className="text-[9px] text-sky-400/80 font-mono px-1 rounded bg-sky-500/10">
                      {(note.score * 100).toFixed(0)}%
                    </span>
                  )}
                  <button
                    onClick={(e) => handleCopy(e, note)}
                    className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-colors"
                    title="Copier en Markdown"
                  >
                    {copiedId === note.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                {note.summary}
              </p>

              <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1">
                <span className="truncate max-w-[180px]">{note.source}</span>
                <div className="flex items-center gap-1 shrink-0">
                  {note.tags.slice(0, 3).map((tag) => (
                    <button
                      key={tag}
                      onClick={(e) => {
                        e.stopPropagation();
                        filterByTag(tag);
                      }}
                      className={`px-1.5 py-0.5 rounded transition-colors ${
                        selectedTag === tag
                          ? 'bg-sky-500/20 text-sky-300 font-medium'
                          : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200'
                      }`}
                      title={`Filtrer par #${tag}`}
                    >
                      #{tag}
                    </button>
                  ))}
                  {note.tags.length > 3 && (
                    <span className="text-[9px] text-slate-500">+{note.tags.length - 3}</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Note Detail Modal */}
      <AnimatePresence>
        {activeNote && (
          <NoteDetailModal
            note={activeNote}
            onClose={() => setActiveNote(null)}
            onSelectTag={(tag) => filterByTag(tag)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

import React, { useEffect, useRef } from 'react';
import { Mascot } from './Mascot';
import { useDropStore } from '../../core/stores/useDropStore';
import { useEchoStore } from '../../core/stores/useEchoStore';
import { useViewStore } from '../../core/stores/useViewStore';
import { useSignalStore } from '../../core/stores/useSignalStore';
import {
  SURFACES,
  SURFACE_CARD,
  SURFACE_CARD_HOVER,
} from '../../design-system/tokens';
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Zap,
  ArrowRight,
  X,
  Check,
} from 'lucide-react';

const TICKER_INTERVAL_MS = 6000;

/**
 * Defensive pure helper detecting raw JSON dumps or Algolia metadata payloads.
 */
export function isJsonPayload(text?: string | null): boolean {
  if (!text) return false;
  const trimmed = text.trim();
  return trimmed.startsWith('{') || trimmed.includes('_highlightResult') || trimmed.includes('"objectID"');
}

/**
 * Truncate filename in the middle to prevent visual overflow while preserving extension.
 */
function truncateMiddle(str: string, maxLength: number = 20): string {
  if (str.length <= maxLength) return str;
  const charsToShow = maxLength - 3;
  const frontChars = Math.ceil(charsToShow / 2);
  const backChars = Math.floor(charsToShow / 2);
  return str.slice(0, frontChars) + '...' + str.slice(str.length - backChars);
}

export const HomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const {
    dropStatus,
    fileName,
    mascotEmotion,
    errorMessage,
    setHover,
    setError,
    ingestFileInPlace,
  } = useDropStore();

  const { notes, latestNote, fetchNotes } = useEchoStore();
  const currentSignal = useSignalStore((state) => state.currentSignal);
  const dismissCurrent = useSignalStore((state) => state.dismissCurrent);
  const isSignalLoading = useSignalStore((state) => state.isLoading);

  // Calmed ticker rotation state with pause on hover
  const [tickerIndex, setTickerIndex] = React.useState<number>(0);
  const [isTickerPaused, setIsTickerPaused] = React.useState<boolean>(false);

  useEffect(() => {
    if (notes.length <= 1 || isTickerPaused) return;

    const interval = setInterval(() => {
      setTickerIndex((prev) => (prev + 1) % notes.length);
    }, TICKER_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [notes.length, isTickerPaused]);

  // Derived current note for ticker ensuring safe index boundary
  const activeTickerNote = notes.length > 0 ? notes[tickerIndex % notes.length] : latestNote;
  const cleanSummary = currentSignal?.summary && !isJsonPayload(currentSignal.summary) ? currentSignal.summary : null;

  // Derived mascot emotion prioritizing active drag/ingestion/error, then blindspot alert, then idle
  const displayEmotion =
    dropStatus === 'hover'
      ? 'hover_drop'
      : dropStatus === 'processing'
      ? 'ingesting'
      : dropStatus === 'ready'
      ? 'ready'
      : dropStatus === 'error'
      ? 'error'
      : currentSignal !== null
      ? 'alert'
      : mascotEmotion;

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setHover(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setHover(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setHover(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const realPath = window.ekkoAPI?.getDroppedFilePath
        ? window.ekkoAPI.getDroppedFilePath(file)
        : '';

      console.log('[Drop:Event] Chemin absolu extrait via webUtils :', realPath);

      if (!realPath) {
        setError('Impossible de résoudre le chemin système du fichier.');
        return;
      }

      await ingestFileInPlace(realPath);
    }
  };

  const handleBrowseFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const realPath = window.ekkoAPI?.getDroppedFilePath
        ? window.ekkoAPI.getDroppedFilePath(file)
        : '';

      if (!realPath) {
        setError('Impossible de résoudre le chemin système du fichier.');
        return;
      }

      await ingestFileInPlace(realPath);
      e.target.value = '';
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="w-full h-full flex gap-4 p-2.5 select-none overflow-hidden relative"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.md,.markdown,.txt"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Volet Gauche (~36 % / ~215 px) — Mascotte vectorielle purement centrée & sans badge textuel */}
      <div className="w-[36%] h-full flex items-center justify-center relative shrink-0">
        {/* Soft radial shine */}
        <div className="absolute inset-0 bg-radial from-sky-400/[0.04] via-transparent to-transparent pointer-events-none" />

        <Mascot emotion={displayEmotion} />
      </div>

      {/* Volet Droit — Espace réactif métamorphe */}
      <div className="flex-1 h-full flex flex-col overflow-hidden relative">
        {dropStatus === 'hover' ? (
          /* État 2 : Au survol de fichier (Option B plein cadre) */
          <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneHover} flex flex-col items-center justify-center gap-1.5 text-center select-none transition-all`}>
            <UploadCloud className="w-7 h-7 text-sky-300 animate-bounce" />
            <span className="text-xs font-semibold text-sky-200">
              Relâcher pour absorber
            </span>
            <span className="text-[10px] text-sky-400/70">
              PDF, notes Markdown ou texte brut (.txt)
            </span>
          </div>
        ) : dropStatus === 'processing' ? (
          /* État 3 : En cours de distillation (async) */
          <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneProcessing} flex flex-col items-center justify-center gap-2 text-center p-3 relative select-none`}>
            <div className="absolute inset-0 bg-sky-400/[0.03] animate-pulse rounded-xl pointer-events-none" />
            <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
            <div className="flex flex-col z-10 max-w-[280px]">
              <span className="text-xs text-slate-200 font-medium">
                Distillation de {fileName ? truncateMiddle(fileName, 20) : 'document'} en cours...
              </span>
              <span className="text-[10px] text-sky-400/80 mt-0.5 animate-pulse">
                Extraction et synthèse cognitives
              </span>
            </div>
          </div>
        ) : dropStatus === 'ready' ? (
          /* État 4 : Succès réel (arrivée de la note dans SQLite) */
          <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneReady} flex flex-col items-center justify-center gap-1.5 text-center p-3 select-none`}>
            <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            <span className="text-xs text-emerald-300 font-semibold">
              Document absorbé dans le tampon cognitif ✓
            </span>
          </div>
        ) : dropStatus === 'error' ? (
          /* État 5 : Erreur */
          <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneError} flex flex-col items-center justify-center gap-1 text-center p-3 select-none`}>
            <AlertCircle className="w-5 h-5 text-red-400 mb-0.5" />
            <span className="text-[11px] text-red-300 font-semibold">
              {errorMessage || 'Format non supporté'}
            </span>
            <span className="text-[9px] text-slate-400">
              PDF, Markdown (.md) ou texte brut (.txt) uniquement
            </span>
          </div>
        ) : currentSignal ? (
          /* État Veilleur : Alerte Proactive d'Angle Mort (UC-1) */
          <div className={`w-full h-full rounded-xl ${SURFACES.alertCard} flex flex-col justify-between p-3 select-none relative overflow-hidden transition-all shadow-[0_4px_20px_rgba(245,158,11,0.06)]`}>
            {/* Header: Badge ambre + source */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-300">
                <Zap className="w-3 h-3 text-amber-400" />
                <span className="text-[10px] font-semibold tracking-wide uppercase">
                  Angle mort identifié
                </span>
              </div>
              <span className="text-[10px] text-amber-400/80 font-medium truncate max-w-[130px] uppercase tracking-wider">
                {currentSignal.source_type}
              </span>
            </div>

            {/* Content: Titre éclatant + synthèse */}
            <div className="flex flex-col gap-1 my-0.5">
              <h3 className="text-sm font-medium text-white line-clamp-2 leading-snug">
                {currentSignal.title}
              </h3>
              {cleanSummary && (
                <p className="text-xs text-white/60 line-clamp-2 leading-relaxed">
                  {cleanSummary}
                </p>
              )}
            </div>

            {/* Actions: Écarter (secondaire) & Archiver (primaire) */}
            <div className="flex items-center justify-end gap-2 pt-1 border-t border-white/[0.04]">
              <button
                onClick={() => dismissCurrent('discard')}
                disabled={isSignalLoading}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-colors text-xs font-medium cursor-pointer"
                title="Écarter cette découverte"
              >
                <X className="w-3.5 h-3.5" />
                <span>Écarter</span>
              </button>

              <button
                onClick={() => dismissCurrent('archive')}
                disabled={isSignalLoading}
                className="flex items-center gap-1 px-3 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 hover:bg-amber-500/25 transition-all text-xs font-semibold shadow-[0_0_12px_rgba(245,158,11,0.15)] cursor-pointer"
                title="Conserver et archiver dans le PKM"
              >
                <Check className="w-3.5 h-3.5 text-amber-400" />
                <span>Archiver</span>
              </button>
            </div>
          </div>
        ) : (
          /* État 1 : Au repos (Option A — Split 65/35) */
          <div className="w-full h-full flex flex-col gap-2">
            {/* Partie supérieure (~65 %) : invitation au drop transparente */}
            <div
              onClick={handleBrowseFile}
              className={`flex-[0.65] rounded-xl flex flex-col items-center justify-center gap-1 text-center p-2 transition-colors cursor-pointer select-none ${SURFACES.dropzoneIdle}`}
            >
              <UploadCloud className="w-5 h-5 text-sky-400/70 mb-0.5 transition-colors" />
              <span className="text-xs font-semibold text-slate-200">
                Glisser un document ou une URL
              </span>
              <span className="text-[10px] text-slate-400">
                PDF, notes Markdown, articles web (in-place)
              </span>
            </div>

            {/* Partie inférieure (~35 %) : ligne "Dernier Écho" posée à plat */}
            <div
              onClick={() => setViewMode('echo')}
              onMouseEnter={() => setIsTickerPaused(true)}
              onMouseLeave={() => setIsTickerPaused(false)}
              className={`flex-[0.35] rounded-xl ${SURFACE_CARD} ${SURFACE_CARD_HOVER} px-3 py-1.5 flex items-center justify-between cursor-pointer transition-all group select-none`}
            >
              <div className="flex items-center gap-2.5 min-w-0 pr-2">
                <div className="p-1 rounded-lg bg-amber-400/10 text-amber-400 shrink-0">
                  <Zap className="w-3.5 h-3.5" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-[9px] text-slate-500 font-medium uppercase tracking-wider">
                    Dernier Écho
                  </span>
                  <p className="text-xs text-slate-200 font-medium truncate">
                    {activeTickerNote?.title || 'Tampon cognitif vide'}
                  </p>
                </div>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-sky-300 group-hover:translate-x-0.5 transition-all shrink-0" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

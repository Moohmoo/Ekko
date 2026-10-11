import React, { useEffect, useRef } from 'react';
import { Mascot } from './Mascot';
import { useDropStore } from '../../core/stores/useDropStore';
import { useEchoStore } from '../../core/stores/useEchoStore';
import { useViewStore } from '../../core/stores/useViewStore';
import {
  SURFACES,
  SURFACE_CARD,
  SURFACE_CARD_HOVER,
  STATUS_CONFIG,
} from '../../design-system/tokens';
import {
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Zap,
  ArrowRight,
} from 'lucide-react';

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

  const { latestNote, fetchNotes } = useEchoStore();

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

  // Derive stable status badge under mascot
  const statusKey =
    dropStatus === 'hover'
      ? 'hover'
      : dropStatus === 'processing'
      ? 'processing'
      : dropStatus === 'ready'
      ? 'ready'
      : dropStatus === 'error'
      ? 'error'
      : 'idle';

  const currentStatus = STATUS_CONFIG[statusKey];

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

      {/* Volet Gauche (36 %) — Mascotte continue sans séparateur vertical */}
      <div className="w-[36%] h-full flex flex-col items-center justify-between relative shrink-0">
        {/* Soft radial shine */}
        <div className="absolute inset-0 bg-radial from-sky-400/[0.04] via-transparent to-transparent pointer-events-none" />

        <div className="flex-1 flex items-center justify-center transform scale-[0.70] origin-center">
          <Mascot emotion={mascotEmotion} />
        </div>

        {/* Badge d'état sous la mascotte à gabarit stable (sans texte long ni coupure) */}
        <div className="flex items-center justify-center shrink-0">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.06] shrink-0 h-6">
            <span className={`w-1.5 h-1.5 rounded-full ${currentStatus.dotClass}`} />
            <span className="text-[10px] text-slate-300 font-medium tracking-tight whitespace-nowrap">
              {currentStatus.label}
            </span>
          </div>
        </div>
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
                    {latestNote?.title || 'Tampon cognitif vide'}
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

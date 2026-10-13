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

/**
 * Universal file:// URI decoder adhering to RFC 8089 across Linux, macOS and Windows.
 */
function parseFileUriToPath(uri: string): string {
  try {
    const url = new URL(uri);
    if (url.protocol !== 'file:') return '';
    let pathname = decodeURIComponent(url.pathname);
    // On Windows, /C:/path -> C:/path
    if (/^\/[a-zA-Z]:/.test(pathname)) {
      pathname = pathname.slice(1);
    }
    return pathname;
  } catch {
    return '';
  }
}

export const HomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isIngesting, setIsIngesting] = React.useState<boolean>(false);

  const {
    dropStatus,
    fileName,
    mascotEmotion,
    forcedEmotion,
    errorMessage,
    setHover,
    setError,
    ingestFileInPlace,
    ingestUrlInPlace,
  } = useDropStore();

  const { latestNote, fetchNotes } = useEchoStore();
  const currentSignal = useSignalStore((state) => state.currentSignal);
  const totalCount = useSignalStore((state) => state.totalCount);
  const dismissCurrent = useSignalStore((state) => state.dismissCurrent);
  const resolveAll = useSignalStore((state) => state.resolveAll);
  const isSignalResolving = useSignalStore((state) => state.isResolving);

  const cleanSummary = currentSignal?.summary && !isJsonPayload(currentSignal.summary) ? currentSignal.summary : null;

  // Derived mascot emotion prioritizing dev test forcedEmotion, then active drag/ingestion/error, then blindspot alert, then idle
  const displayEmotion =
    forcedEmotion !== null
      ? forcedEmotion
      : dropStatus === 'hover'
      ? 'hover_drop'
      : dropStatus === 'processing' || isIngesting
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

  // Global paste handler on Home view for rapid URL absorption (Ctrl+V)
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      // Do not intercept paste if an input or textarea is currently focused or if ingestion in progress
      if (isIngesting) return;

      const activeEl = document.activeElement;
      if (
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          (activeEl as HTMLElement).isContentEditable)
      ) {
        return;
      }

      const pastedText = e.clipboardData?.getData('text/plain') || '';
      const trimmed = pastedText.trim();
      const firstLine = trimmed.split('\n')[0].trim();

      if (firstLine.startsWith('http://') || firstLine.startsWith('https://')) {
        e.preventDefault();
        console.log('[Paste:Event] Ingestion URL détectée via presse-papiers :', firstLine);
        setIsIngesting(true);
        try {
          await ingestUrlInPlace(firstLine);
        } finally {
          setIsIngesting(false);
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [ingestUrlInPlace, isIngesting]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isIngesting) {
      setHover(true);
    }
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

    if (isIngesting) {
      console.warn('[Drop:Event] Ingestion déjà en cours, dépôt ignoré.');
      return;
    }

    setIsIngesting(true);
    try {
      let resolvedPath = '';

      // Priorité 1 : Fichier DOM via webUtils / legacy File.path
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        resolvedPath = window.ekkoAPI?.getDroppedFilePath
          ? window.ekkoAPI.getDroppedFilePath(file)
          : '';

        console.log('[Drop:Event] Chemin extrait via getDroppedFilePath :', resolvedPath);
      }

      // Priorité 2 : URI drop (text/uri-list, text/plain ou URL)
      const rawUri =
        e.dataTransfer.getData('text/uri-list') ||
        e.dataTransfer.getData('text/plain') ||
        e.dataTransfer.getData('URL') ||
        '';

      const cleanedUri = rawUri
        .split('\n')
        .map((l) => l.trim())
        .find((l) => l.length > 0 && !l.startsWith('#'));

      // Fallback universel multi-OS si webUtils a renvoyé vide (ex: premier drop Linux Nautilus sans focus préalable)
      if (!resolvedPath && cleanedUri && cleanedUri.startsWith('file://')) {
        resolvedPath = parseFileUriToPath(cleanedUri);
        console.log('[Drop:Event] Chemin résolu via fallback file:// URI :', resolvedPath);
      }

      if (resolvedPath) {
        await ingestFileInPlace(resolvedPath);
        return;
      }

      // Priorité 3 : URL web distante (http:// ou https://)
      if (cleanedUri && (cleanedUri.startsWith('http://') || cleanedUri.startsWith('https://'))) {
        console.log('[Drop:Event] URL extraite via drag-and-drop :', cleanedUri);
        await ingestUrlInPlace(cleanedUri);
        return;
      }

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        setError('Impossible de résoudre le chemin système du fichier.');
      } else {
        setError('Format non supporté · Déposez un fichier local ou une URL valide');
      }
    } finally {
      setIsIngesting(false);
    }
  };

  const handleBrowseFile = () => {
    if (isIngesting) return;
    fileInputRef.current?.click();
  };

  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isIngesting) return;
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const realPath = window.ekkoAPI?.getDroppedFilePath
        ? window.ekkoAPI.getDroppedFilePath(file)
        : '';

      if (!realPath) {
        setError('Impossible de résoudre le chemin système du fichier.');
        return;
      }

      setIsIngesting(true);
      try {
        await ingestFileInPlace(realPath);
      } finally {
        setIsIngesting(false);
      }
      e.target.value = '';
    }
  };

  const [isHoverWoken, setIsHoverWoken] = React.useState<boolean>(false);
  const sleepTimerRef = useRef<NodeJS.Timeout | null>(null);
  const mascotContainerRef = useRef<HTMLDivElement | null>(null);
  const rafIdRef = useRef<number | null>(null);

  // Global viewport pointer tracking: completely bypasses React re-render cycle via direct CSS variable mutation
  useEffect(() => {
    const handleGlobalPointerMove = (e: PointerEvent) => {
      // 1. Cancel any pending sleep timer
      if (sleepTimerRef.current) {
        clearTimeout(sleepTimerRef.current);
        sleepTimerRef.current = null;
      }

      // 2. Wake up mascot if sleeping (only triggers state update once when transitioning from sleeping to awake)
      setIsHoverWoken((prev) => (prev ? prev : true));

      // 3. Compute delta relative to mascot center and apply directly to CSS variables on animation frame
      if (mascotContainerRef.current) {
        const container = mascotContainerRef.current;
        if (rafIdRef.current) {
          cancelAnimationFrame(rafIdRef.current);
        }

        rafIdRef.current = requestAnimationFrame(() => {
          const rect = container.getBoundingClientRect();
          const mascotCenterX = rect.left + rect.width / 2;
          const mascotCenterY = rect.top + rect.height / 2;
          const deltaX = e.clientX - mascotCenterX;
          const deltaY = e.clientY - mascotCenterY;
          const rawHypot = Math.hypot(deltaX, deltaY);

          let eyeDx = 0;
          let eyeDy = 0;

          if (rawHypot > 0.1) {
            const angle = Math.atan2(deltaY, deltaX);
            const sensitivity = 34.0;
            const distance = Math.min(rawHypot / sensitivity, 3.5);
            eyeDx = Math.cos(angle) * distance;
            eyeDy = Math.sin(angle) * distance;
          }

          container.style.setProperty('--eye-dx', `${eyeDx.toFixed(2)}px`);
          container.style.setProperty('--eye-dy', `${eyeDy.toFixed(2)}px`);
        });
      }
    };

    const handleGlobalMouseLeave = () => {
      if (mascotContainerRef.current) {
        mascotContainerRef.current.style.removeProperty('--eye-dx');
        mascotContainerRef.current.style.removeProperty('--eye-dy');
      }
      if (sleepTimerRef.current) {
        clearTimeout(sleepTimerRef.current);
      }
      // Soft delay of 1.2s before going back to sleep (‿ ‿)
      sleepTimerRef.current = setTimeout(() => {
        setIsHoverWoken(false);
        sleepTimerRef.current = null;
      }, 1200);
    };

    window.addEventListener('pointermove', handleGlobalPointerMove, { passive: true });
    document.addEventListener('mouseleave', handleGlobalMouseLeave);

    return () => {
      window.removeEventListener('pointermove', handleGlobalPointerMove);
      document.removeEventListener('mouseleave', handleGlobalMouseLeave);
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
      if (sleepTimerRef.current) {
        clearTimeout(sleepTimerRef.current);
      }
    };
  }, []);

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="w-full h-full flex gap-4 p-2.5 select-none overflow-hidden relative cursor-default"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.md,.markdown,.txt"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Volet Gauche (~36 % / ~215 px) — Mascotte vectorielle purement centrée */}
      <div
        ref={mascotContainerRef}
        className="w-[36%] h-full flex items-center justify-center relative shrink-0 cursor-default pointer-events-none"
      >
        {/* Soft radial shine */}
        <div className="absolute inset-0 bg-radial from-sky-400/[0.04] via-transparent to-transparent pointer-events-none" />

        <Mascot
          emotion={displayEmotion}
          isWokenByHover={isHoverWoken}
        />
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
        ) : dropStatus === 'processing' || isIngesting ? (
          /* État 3 : En cours de distillation (async) / Verrou d'ingestion */
          <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneProcessing} flex flex-col items-center justify-center gap-2 text-center p-3 relative select-none pointer-events-none`}>
            <div className="absolute inset-0 bg-sky-400/[0.03] animate-pulse rounded-xl pointer-events-none" />
            <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
            <div className="flex flex-col z-10 max-w-[280px]">
              <span className="text-xs text-slate-200 font-medium">
                {fileName ? `Distillation de ${truncateMiddle(fileName, 20)} en cours...` : 'Ingestion en cours...'}
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
          <div className={`w-full h-full rounded-xl ${SURFACES.alertCard} flex flex-col justify-between p-3 select-none relative overflow-hidden transition-all shadow-[0_4px_20px_rgba(245,158,11,0.06)] min-h-0`}>
            {/* Header: Badge ambre + source + compteur (Fixe) */}
            <div className="flex items-center justify-between gap-2 shrink-0">
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-300">
                <Zap className="w-3 h-3 text-amber-400" />
                <span className="text-[10px] font-semibold tracking-wide uppercase">
                  {totalCount > 1 ? `Angle mort identifié · 1 / ${totalCount}` : 'Angle mort identifié'}
                </span>
              </div>
              <span className="text-[10px] text-amber-400/80 font-medium truncate max-w-[130px] uppercase tracking-wider">
                {currentSignal.source_type}
              </span>
            </div>

            {/* Content: Titre éclatant + synthèse (Flexible et scroll-safe) */}
            <div className="flex flex-col gap-1 my-auto min-h-0 overflow-hidden">
              <h3 className="text-xs font-semibold text-white line-clamp-2 leading-tight">
                {currentSignal.title}
              </h3>
              {cleanSummary && (
                <p className="text-[11px] text-zinc-400 line-clamp-2 mt-1 leading-snug">
                  {cleanSummary}
                </p>
              )}
            </div>

            {/* Actions: Tout écarter (si > 10) | Écarter & Archiver (Fixe en bas) */}
            <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/[0.06] shrink-0">
              {totalCount > 10 ? (
                <button
                  onClick={() => resolveAll('discard')}
                  disabled={isSignalResolving}
                  className="text-[10px] text-slate-400 hover:text-slate-200 transition-colors font-medium cursor-pointer"
                  title="Écarter tous les signaux en attente"
                >
                  Tout écarter ({totalCount})
                </button>
              ) : (
                <div />
              )}

              <div className="flex items-center gap-2">
                <button
                  onClick={() => dismissCurrent('discard')}
                  disabled={isSignalResolving}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-colors text-xs font-medium cursor-pointer"
                  title="Écarter cette découverte"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Écarter</span>
                </button>

                <button
                  onClick={() => dismissCurrent('archive')}
                  disabled={isSignalResolving}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 hover:bg-amber-500/25 transition-all text-xs font-semibold shadow-[0_0_12px_rgba(245,158,11,0.15)] cursor-pointer"
                  title="Conserver et archiver dans le PKM"
                >
                  <Check className="w-3.5 h-3.5 text-amber-400" />
                  <span>Archiver</span>
                </button>
              </div>
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

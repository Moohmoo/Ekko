import React, { useEffect, useRef, useState } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useDropStore } from '../../../core/stores/useDropStore';
import { SURFACES } from '../../../design-system/tokens';
import { LastNoteCard } from './LastNoteCard';

interface DropZoneProps {
  latestNoteTitle?: string | null;
  onNavigateBuffer: () => void;
}

function truncateMiddle(str: string, maxLength: number = 20): string {
  if (str.length <= maxLength) return str;
  const charsToShow = maxLength - 3;
  const frontChars = Math.ceil(charsToShow / 2);
  const backChars = Math.floor(charsToShow / 2);
  return str.slice(0, frontChars) + '...' + str.slice(str.length - backChars);
}

function parseFileUriToPath(uri: string): string {
  try {
    const url = new URL(uri);
    if (url.protocol !== 'file:') return '';
    let pathname = decodeURIComponent(url.pathname);
    if (/^\/[a-zA-Z]:/.test(pathname)) {
      pathname = pathname.slice(1);
    }
    return pathname;
  } catch {
    return '';
  }
}

/**
 * Universal DropZone component managing multi-OS drag-and-drop,
 * clipboard URL absorption (Ctrl+V), and manual file picking.
 */
export const DropZone: React.FC<DropZoneProps> = ({
  latestNoteTitle,
  onNavigateBuffer,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isIngesting, setIsIngesting] = useState<boolean>(false);

  const {
    dropStatus,
    fileName,
    errorMessage,
    setHover,
    setError,
    ingestFileInPlace,
    ingestUrlInPlace,
  } = useDropStore();

  // Global paste handler on Home view for rapid URL absorption (Ctrl+V)
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
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

    if (isIngesting) return;

    setIsIngesting(true);
    try {
      let resolvedPath = '';

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        resolvedPath = window.ekkoAPI?.getDroppedFilePath
          ? window.ekkoAPI.getDroppedFilePath(file)
          : '';
      }

      const rawUri =
        e.dataTransfer.getData('text/uri-list') ||
        e.dataTransfer.getData('text/plain') ||
        e.dataTransfer.getData('URL') ||
        '';

      const cleanedUri = rawUri
        .split('\n')
        .map((l) => l.trim())
        .find((l) => l.length > 0 && !l.startsWith('#'));

      if (!resolvedPath && cleanedUri && cleanedUri.startsWith('file://')) {
        resolvedPath = parseFileUriToPath(cleanedUri);
      }

      if (resolvedPath) {
        await ingestFileInPlace(resolvedPath);
        return;
      }

      if (cleanedUri && (cleanedUri.startsWith('http://') || cleanedUri.startsWith('https://'))) {
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

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="flex-1 h-full flex flex-col overflow-hidden relative"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.md,.markdown,.txt"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {dropStatus === 'hover' ? (
        /* State 2 : On drag-over */
        <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneHover} flex flex-col items-center justify-center gap-1.5 text-center select-none transition-all`}>
          <UploadCloud className="w-7 h-7 text-sky-300 animate-bounce" />
          <span className="text-xs font-semibold text-sky-200">
            Release to absorb
          </span>
          <span className="text-[10px] text-sky-400/70">
            PDF, Markdown notes, or plain text (.txt)
          </span>
        </div>
      ) : dropStatus === 'processing' || isIngesting ? (
        /* State 3 : Active distillation */
        <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneProcessing} flex flex-col items-center justify-center gap-2 text-center p-3 relative select-none pointer-events-none`}>
          <div className="absolute inset-0 bg-sky-400/[0.03] animate-pulse rounded-xl pointer-events-none" />
          <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
          <div className="flex flex-col z-10 max-w-[280px]">
            <span className="text-xs text-slate-200 font-medium">
              {fileName ? `Distilling ${truncateMiddle(fileName, 20)}...` : 'Ingesting...'}
            </span>
            <span className="text-[10px] text-sky-400/80 mt-0.5 animate-pulse">
              Cognitive extraction & distillation
            </span>
          </div>
        </div>
      ) : dropStatus === 'ready' ? (
        /* State 4 : Success */
        <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneReady} flex flex-col items-center justify-center gap-1.5 text-center p-3 select-none`}>
          <CheckCircle2 className="w-6 h-6 text-emerald-400" />
          <span className="text-xs text-emerald-300 font-semibold">
            Document absorbed into cognitive buffer ✓
          </span>
        </div>
      ) : dropStatus === 'error' ? (
        /* State 5 : Error */
        <div className={`w-full h-full rounded-xl ${SURFACES.dropzoneError} flex flex-col items-center justify-center gap-1 text-center p-3 select-none`}>
          <AlertCircle className="w-5 h-5 text-red-400 mb-0.5" />
          <span className="text-[11px] text-red-300 font-semibold">
            {errorMessage || 'Unsupported format'}
          </span>
          <span className="text-[9px] text-slate-400">
            PDF, Markdown (.md), or plain text (.txt) only
          </span>
        </div>
      ) : (
        /* State 1 : Idle (Split 65/35) */
        <div className="w-full h-full flex flex-col gap-2">
          {/* Top part (~65 %) : Drop invitation */}
          <div
            onClick={handleBrowseFile}
            className={`flex-[0.65] rounded-xl flex flex-col items-center justify-center gap-1 text-center p-2 transition-colors cursor-pointer select-none ${SURFACES.dropzoneIdle}`}
          >
            <UploadCloud className="w-5 h-5 text-sky-400/70 mb-0.5 transition-colors" />
            <span className="text-xs font-semibold text-slate-200">
              Drop a file or paste URL
            </span>
            <span className="text-[10px] text-slate-400">
              PDF, Markdown notes, web articles (in-place)
            </span>
          </div>

          {/* Bottom part (~35 %) : latest note */}
          <LastNoteCard
            title={latestNoteTitle}
            onClick={onNavigateBuffer}
          />
        </div>
      )}
    </div>
  );
};

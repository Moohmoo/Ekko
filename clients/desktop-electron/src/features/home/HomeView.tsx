import React, { useEffect } from 'react';
import { Mascot } from './Mascot';
import { useDropStore } from '../../core/stores/useDropStore';
import { useEchoStore } from '../../core/stores/useEchoStore';
import { useViewStore } from '../../core/stores/useViewStore';
import {
  UploadCloud,
  CheckCircle2,
  Zap,
  ArrowRight,
} from 'lucide-react';

export const HomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);

  const {
    dropStatus,
    progress,
    fileName,
    mascotEmotion,
    statusMessage,
    setHover,
    ingestFileInPlace,
  } = useDropStore();

  const { latestNote, fetchNotes } = useEchoStore();

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setHover(true);
  };

  const handleDragLeave = () => {
    setHover(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setHover(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const filePath = (file as unknown as { path?: string }).path || file.name;
      await ingestFileInPlace(filePath);
      await fetchNotes();
    }
  };

  return (
    <div className="w-full h-full flex gap-2.5 select-none overflow-hidden">
      {/* Volet Gauche (40 % / ~225 px) — Capsule Mascotte en relief */}
      <div className="w-[225px] h-full rounded-2xl bg-[#141824] border border-white/[0.08] flex flex-col items-center justify-between p-2.5 relative overflow-hidden shadow-inner">
        {/* Soft radial shine */}
        <div className="absolute inset-0 bg-radial from-sky-400/[0.06] via-transparent to-transparent pointer-events-none" />

        <div className="flex-1 flex items-center justify-center transform scale-[0.78] origin-center -my-2">
          <Mascot emotion={mascotEmotion} />
        </div>

        {/* Micro-statut discret sous la mascotte */}
        <div className="flex items-center gap-1.5 z-10 px-2 py-0.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              mascotEmotion === 'ready'
                ? 'bg-emerald-400'
                : mascotEmotion === 'ingesting'
                ? 'bg-sky-400 animate-ping'
                : mascotEmotion === 'hover_drop'
                ? 'bg-sky-300'
                : 'bg-sky-400/70'
            }`}
          />
          <span className="text-[10px] text-slate-300 font-medium tracking-tight">
            {statusMessage}
          </span>
        </div>
      </div>

      {/* Volet Droit (60 % / ~350 px) — Espace épuré en 2 blocs aérés */}
      <div className="flex-1 h-full flex flex-col gap-2 overflow-hidden">
        {/* Bloc 1 : Grande Zone "Drop & Forget" (environ 65 % de la hauteur droite) */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`flex-[0.65] rounded-xl border transition-all p-3 flex flex-col items-center justify-center relative overflow-hidden select-none ${
            dropStatus === 'hover'
              ? 'bg-sky-500/15 border-sky-400 scale-[1.01]'
              : dropStatus === 'uploading' || dropStatus === 'distilling'
              ? 'bg-[#141824] border-sky-500/40'
              : dropStatus === 'success'
              ? 'bg-emerald-950/20 border-emerald-500/40'
              : 'bg-[#141824] border-dashed border-white/10 hover:border-sky-400/40 hover:bg-white/[0.02]'
          }`}
        >
          {dropStatus === 'uploading' || dropStatus === 'distilling' ? (
            <div className="w-full flex flex-col items-center justify-center gap-1.5 px-3">
              <div className="w-full flex items-center justify-between text-[11px]">
                <span className="text-sky-300 font-medium truncate max-w-[180px]">
                  {fileName || 'Document'}
                </span>
                <span className="font-mono text-sky-400 text-xs">{progress}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-sky-400 h-full rounded-full transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-400 mt-0.5">Distillation in-place en cours...</span>
            </div>
          ) : dropStatus === 'success' ? (
            <div className="flex flex-col items-center justify-center gap-1.5 text-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-xs text-emerald-300 font-medium">
                Document assimilé et indexé ✓
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-1 text-center pointer-events-none">
              <UploadCloud
                className={`w-6 h-6 transition-colors mb-0.5 ${
                  dropStatus === 'hover' ? 'text-sky-300 animate-bounce' : 'text-sky-400/70'
                }`}
              />
              <span className="text-xs font-semibold text-slate-200">
                {dropStatus === 'hover' ? 'Relâcher pour absorber' : 'Glisser un document ou une URL'}
              </span>
              <span className="text-[10px] text-slate-400">
                PDF, notes Markdown, articles web (in-place)
              </span>
            </div>
          )}
        </div>

        {/* Bloc 2 : Carte "Dernier Écho" (environ 35 % de la hauteur droite) */}
        <div
          onClick={() => setViewMode('echo')}
          className="flex-[0.35] rounded-xl bg-[#141824] hover:bg-[#161b26] border border-white/[0.08] hover:border-sky-400/40 px-3 py-2 flex items-center justify-between cursor-pointer transition-all group"
        >
          <div className="flex items-center gap-2.5 min-w-0 pr-2">
            <div className="p-1.5 rounded-lg bg-amber-400/10 text-amber-400 shrink-0">
              <Zap className="w-3.5 h-3.5" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
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
    </div>
  );
};

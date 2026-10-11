import React, { useEffect } from 'react';
import { Mascot } from './Mascot';
import { useDaemonStore } from '../../core/stores/useDaemonStore';
import { useDropStore } from '../../core/stores/useDropStore';
import { useEchoStore } from '../../core/stores/useEchoStore';
import { useViewStore } from '../../core/stores/useViewStore';
import {
  UploadCloud,
  CheckCircle2,
  Radio,
  Zap,
  Activity,
  ArrowRight,
} from 'lucide-react';

export const HomeView: React.FC = () => {
  const isOnline = useDaemonStore((state) => state.isOnline);
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

      {/* Volet Droit (60 % / ~355 px) — Grille Bento 2x2 ultra-dense */}
      <div className="flex-1 h-full grid grid-cols-2 grid-rows-2 gap-2 overflow-hidden">
        {/* Tuile 1 : Drop & Forget in-place */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`rounded-xl border transition-all p-2 flex flex-col justify-between relative overflow-hidden ${
            dropStatus === 'hover'
              ? 'bg-sky-500/15 border-sky-400 scale-[1.01]'
              : dropStatus === 'uploading' || dropStatus === 'distilling'
              ? 'bg-[#141824] border-sky-500/40'
              : dropStatus === 'success'
              ? 'bg-emerald-950/20 border-emerald-500/40'
              : 'bg-[#141824] border-dashed border-sky-400/30 hover:border-sky-400/50 hover:bg-white/[0.02]'
          }`}
        >
          {dropStatus === 'uploading' || dropStatus === 'distilling' ? (
            <div className="h-full flex flex-col justify-between py-0.5">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-sky-300 font-medium truncate max-w-[90px]">
                  {fileName || 'Document'}
                </span>
                <span className="font-mono text-sky-400">{progress}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden my-1">
                <div
                  className="bg-sky-400 h-full rounded-full transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-[9px] text-slate-400">Distillation in-place...</span>
            </div>
          ) : dropStatus === 'success' ? (
            <div className="h-full flex flex-col items-center justify-center gap-1 text-center">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-[10px] text-emerald-300 font-semibold">
                Fiche indexée ✓
              </span>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-slate-200">
                  Drop & Forget
                </span>
                <UploadCloud
                  className={`w-3.5 h-3.5 transition-colors ${
                    dropStatus === 'hover' ? 'text-sky-300' : 'text-sky-400/70'
                  }`}
                />
              </div>
              <p className="text-[9px] text-slate-400 leading-tight">
                {dropStatus === 'hover'
                  ? 'Relâcher pour absorber'
                  : 'Déposer PDF, URL ou note'}
              </p>
            </>
          )}
        </div>

        {/* Tuile 2 : Veilleurs */}
        <div className="rounded-xl bg-[#141824] border border-white/[0.08] p-2 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-slate-200 flex items-center gap-1">
              <Radio className="w-3 h-3 text-sky-400" />
              Veilleurs
            </span>
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
              }`}
              title={isOnline ? 'Veille active' : 'Veille hors ligne'}
            />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-white/[0.04] text-[9px] font-medium text-slate-300 border border-white/5">
              arXiv
            </span>
            <span className="px-1.5 py-0.5 rounded bg-white/[0.04] text-[9px] font-medium text-slate-300 border border-white/5">
              HN
            </span>
            <span className="px-1.5 py-0.5 rounded bg-white/[0.04] text-[9px] font-medium text-slate-300 border border-white/5">
              RSS
            </span>
          </div>
        </div>

        {/* Tuile 3 : Dernier Écho */}
        <div
          onClick={() => setViewMode('echo')}
          className="rounded-xl bg-[#141824] border border-white/[0.08] p-2 flex flex-col justify-between cursor-pointer hover:border-sky-400/40 hover:bg-white/[0.02] transition-colors group"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-slate-200 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" />
              Dernier Écho
            </span>
            <ArrowRight className="w-2.5 h-2.5 text-slate-500 group-hover:text-sky-300 transition-colors" />
          </div>
          <div className="flex flex-col">
            <p className="text-[10px] text-slate-300 font-medium truncate leading-tight">
              {latestNote?.title || 'Tampon cognitif vide'}
            </p>
            <span className="text-[9px] text-slate-500 mt-0.5 truncate">
              {latestNote?.source ? `Source : ${latestNote.source}` : 'Aucune note récente'}
            </span>
          </div>
        </div>

        {/* Tuile 4 : Télémétrie Frugale */}
        <div className="rounded-xl bg-[#141824] border border-white/[0.08] p-2 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-slate-200 flex items-center gap-1">
              <Activity className="w-3 h-3 text-emerald-400" />
              Télémétrie
            </span>
            <span className="text-[9px] font-mono text-emerald-400 font-medium">
              {isOnline ? 'socket OK' : 'offline'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded bg-sky-950/40 text-[9px] font-mono text-sky-300 border border-sky-500/20">
              0M VRAM
            </span>
            <span className="px-1.5 py-0.5 rounded bg-emerald-950/40 text-[9px] font-mono text-emerald-300 border border-emerald-500/20">
              nice +10
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

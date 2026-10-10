import React, { useState } from 'react';
import { ArrowDownToLine, Cpu, Check, AlertCircle } from 'lucide-react';
import { EkkoMascot } from '../mascot/EkkoMascot';
import type { MascotState } from '../../types';

interface HomeViewProps {
  mascotState: MascotState;
  onMascotClick: () => void;
  onDropPayload: (data: string) => void;
  telemetry: {
    niceness: string;
    vramUsageMb: number;
    isOnline: boolean;
  };
  errorMessage?: string | null;
}

export const HomeView: React.FC<HomeViewProps> = ({
  mascotState,
  onMascotClick,
  onDropPayload,
  telemetry,
  errorMessage,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [recentDropName, setRecentDropName] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    let content = '';
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      // In Tauri / WebKit, file object has a non-standard path property containing the absolute file path
      const filePath = (file as unknown as { path?: string }).path;
      content = filePath || file.name;
    } else {
      content = e.dataTransfer.getData('text/plain') || 'Document déposé';
    }

    setRecentDropName(content);
    onDropPayload(content);
    setTimeout(() => setRecentDropName(null), 3000);
  };

  const getStateDescription = () => {
    if (!telemetry.isOnline) {
      return 'Daemon déconnecté · Lancez `uv run ekko daemon`';
    }
    switch (mascotState) {
      case 'idle':
        return 'En veille active · Veilleur d’angles morts';
      case 'ingestion':
        return 'Transmission au daemon et distillation...';
      case 'investigation':
        return 'Analyse des signaux et synthèse PKM...';
      case 'alert':
        return 'Signal saillant détecté !';
      case 'dizzy':
        return 'Hop ! Légèrement étourdi :)';
      default:
        return 'Prêt à capturer vos signaux';
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-between p-5 select-none h-full">
      {/* Top Tagline */}
      <div className="text-center">
        <h2 className="text-xs font-semibold tracking-wider text-slate-300 uppercase">
          Tampon Cognitif Ambiant
        </h2>
        <p className={`text-[11px] mt-0.5 ${telemetry.isOnline ? 'text-slate-400' : 'text-rose-400 font-medium'}`}>
          {getStateDescription()}
        </p>
      </div>

      {/* Central Mascot (Coucou Style Focus) */}
      <div className="my-auto py-2 flex flex-col items-center cursor-pointer" onClick={onMascotClick}>
        <EkkoMascot state={mascotState} size={135} />
      </div>

      {/* Integrated Drop & Forget Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full rounded-2xl border-2 border-dashed p-4 text-center transition-all duration-200 cursor-copy ${
          isDragOver
            ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-[0_0_20px_rgba(0,242,254,0.3)] scale-[1.02]'
            : 'border-white/10 hover:border-cyan-400/50 bg-white/[0.02] hover:bg-white/[0.04] text-slate-400'
        }`}
        title="Glissez une URL, un mémo ou un document ici"
      >
        <div className="flex flex-col items-center justify-center gap-1.5">
          {recentDropName ? (
            <>
              <Check className="w-5 h-5 text-emerald-400" />
              <span className="text-xs text-emerald-300 font-medium truncate max-w-[280px]">
                {recentDropName} absorbé !
              </span>
            </>
          ) : (
            <>
              <ArrowDownToLine
                className={`w-4 h-4 transition-transform duration-200 ${
                  isDragOver ? 'text-cyan-300 scale-125 animate-bounce' : 'text-cyan-400'
                }`}
              />
              <span className="text-xs font-medium text-slate-300">
                {isDragOver ? 'Relâcher pour distiller' : 'Drop & Forget'}
              </span>
              <span className="text-[10px] text-slate-500">
                Glissez un PDF, un article ou une URL pour absorption immédiate
              </span>
            </>
          )}
        </div>
      </div>

      {/* Error banner if drop failed */}
      {errorMessage && (
        <div className="mt-2 w-full flex items-center justify-center gap-1.5 text-[10.5px] text-rose-300 bg-rose-950/40 py-1.5 px-3 rounded-xl border border-rose-800/40 font-mono">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
          <span className="truncate">{errorMessage}</span>
        </div>
      )}

      {/* Bottom Telemetry Chip */}
      <div className="mt-3 flex items-center justify-center gap-2 text-[10px] font-mono text-slate-500">
        <span className="flex items-center gap-1 text-slate-400">
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              backgroundColor: telemetry.isOnline ? '#10b981' : '#f43f5e',
              boxShadow: telemetry.isOnline
                ? '0 0 8px rgba(16, 185, 129, 0.6)'
                : '0 0 8px rgba(244, 63, 94, 0.6)',
            }}
          />
          {telemetry.isOnline ? 'Daemon local actif' : 'Hors ligne'}
        </span>
        <span>·</span>
        <span className="flex items-center gap-1">
          <Cpu className="w-3 h-3 text-cyan-400" />
          {telemetry.niceness}
        </span>
        <span>·</span>
        <span>VRAM {telemetry.vramUsageMb} Mo</span>
      </div>
    </div>
  );
};

export default HomeView;

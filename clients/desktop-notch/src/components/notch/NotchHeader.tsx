import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, ArrowDownToLine, Cpu } from 'lucide-react';
import { EkkoMascot } from '../mascot/EkkoMascot';
import type { MascotState } from '../../types';

interface NotchHeaderProps {
  isExpanded: boolean;
  onToggleExpand: () => void;
  mascotState: MascotState;
  onDropPayload: (data: string) => void;
  telemetry?: {
    niceness: string;
    vramUsageMb: number;
    isOnline: boolean;
  };
}

export const NotchHeader: React.FC<NotchHeaderProps> = ({
  isExpanded,
  onToggleExpand,
  mascotState,
  onDropPayload,
  telemetry = { niceness: 'nice +10', vramUsageMb: 0, isOnline: true },
}) => {
  const [isDragOver, setIsDragOver] = useState(false);

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

    let droppedContent = '';
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      droppedContent = e.dataTransfer.files[0].name;
    } else {
      droppedContent = e.dataTransfer.getData('text/plain') || 'Dropped Item';
    }

    onDropPayload(droppedContent);
  };

  const getSubtext = () => {
    switch (mascotState) {
      case 'idle':
        return 'Veille';
      case 'ingestion':
        return 'Absorption doc...';
      case 'investigation':
        return 'Recherche...';
      case 'alert':
        return 'Signal saillant !';
      case 'drawer':
        return 'Tiroir';
      default:
        return 'Prêt';
    }
  };

  return (
    <motion.header
      layout
      className="glass-notch h-[32px] w-full rounded-b-2xl border-x border-b border-white/10 px-2.5 flex items-center justify-between text-xs transition-colors duration-200 select-none shadow-2xl"
    >
      {/* Left: Micro Mascotte + Logo Badge */}
      <div
        className="flex items-center gap-1.5 cursor-pointer hover:opacity-90 transition-opacity"
        onClick={onToggleExpand}
        title="Ouvrir le tiroir Ekko"
      >
        <EkkoMascot state={mascotState} size="sm" />
        <span className="font-semibold text-slate-200 tracking-wide flex items-center gap-1 text-[11px]">
          Ekko
          <span className="text-slate-500 font-normal">|</span>
          <span className="text-slate-400 font-normal text-[10px] truncate max-w-[80px]">
            {getSubtext()}
          </span>
        </span>
      </div>

      {/* Center: Universal Drop & Forget Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`mx-2 h-[22px] flex-1 max-w-[170px] px-2 rounded-lg border border-dashed flex items-center justify-center gap-1 text-[10px] cursor-copy transition-all duration-200 ${
          isDragOver
            ? 'border-cyan-400 bg-cyan-950/50 text-cyan-200 shadow-[0_0_12px_rgba(0,242,254,0.4)]'
            : 'border-white/15 hover:border-cyan-400/50 bg-black/20 text-slate-400'
        }`}
        title="Déposer un lien, fichier ou note à distiller"
      >
        <ArrowDownToLine
          className={`w-2.5 h-2.5 ${
            isDragOver ? 'text-cyan-300 animate-bounce' : 'text-cyan-400'
          }`}
        />
        <span className="truncate">
          {isDragOver ? 'Relâcher ici' : 'Drop & Forget'}
        </span>
      </div>

      {/* Right: Minimal Telemetry + Expand Button */}
      <div className="flex items-center gap-1.5 text-slate-400">
        <div className="hidden sm:flex items-center gap-1 font-mono text-[9px] bg-slate-900/80 px-1.5 py-0.5 rounded border border-white/5 text-cyan-300">
          <Cpu className="w-2.5 h-2.5" />
          <span>{telemetry.niceness}</span>
        </div>

        <button
          onClick={onToggleExpand}
          className="p-1 rounded-md hover:bg-white/10 hover:text-white transition-colors text-slate-400"
          title={isExpanded ? 'Fermer le tiroir' : 'Ouvrir le tiroir'}
        >
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ type: 'spring', stiffness: 380, damping: 28, mass: 0.8 }}
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </motion.div>
        </button>
      </div>
    </motion.header>
  );
};

export default NotchHeader;

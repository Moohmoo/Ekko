import React, { useState } from 'react';
import { Mascot } from '../../components/Mascot';
import { useDaemonStore } from '../../core/stores/useDaemonStore';
import { UploadCloud } from 'lucide-react';

interface HomeViewProps {
  onFileDrop: (filePath: string) => Promise<void>;
}

export const HomeView: React.FC<HomeViewProps> = ({ onFileDrop }) => {
  const isOnline = useDaemonStore((state) => state.isOnline);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const filePath = (file as unknown as { path?: string }).path || file.name;
      await onFileDrop(filePath);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-between p-5 text-center select-none">
      <div className="flex-1 flex items-center justify-center">
        <Mascot />
      </div>

      {/* Drop & Forget Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`w-full py-6 px-4 rounded-2xl border transition-all flex flex-col items-center justify-center gap-2 ${
          isDragging
            ? 'bg-sky-950/20 border-sky-400 border-dashed scale-[1.02]'
            : 'bg-white/[0.02] border-white/10 border-dashed hover:border-white/20'
        }`}
      >
        <UploadCloud
          className={`w-5 h-5 transition-colors ${
            isDragging ? 'text-sky-400' : 'text-slate-400'
          }`}
        />
        <div>
          <p className="text-xs font-medium text-slate-200">
            Déposer un fichier ou une URL
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Indexation automatique dans le tampon cognitif
          </p>
        </div>
      </div>

      {/* Telemetry Badge connected directly to Zustand */}
      <div className="mt-4 px-3 py-1 rounded-full bg-white/[0.03] border border-white/5 text-[10px] text-slate-500 flex items-center gap-2">
        <span
          className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
            isOnline ? 'bg-emerald-400' : 'bg-red-400'
          }`}
        />
        <span>nice +10 • VRAM 0M • {isOnline ? 'socket OK' : 'déconnecté'}</span>
      </div>
    </div>
  );
};

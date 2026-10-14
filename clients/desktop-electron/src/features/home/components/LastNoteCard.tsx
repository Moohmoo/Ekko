import React from 'react';
import { Layers, ArrowRight } from 'lucide-react';
import { SURFACE_CARD, SURFACE_CARD_HOVER } from '../../../design-system/tokens';

interface LastNoteCardProps {
  title?: string | null;
  onClick: () => void;
}

/**
 * Compact card at the bottom of the home screen displaying the latest distilled note.
 */
export const LastNoteCard: React.FC<LastNoteCardProps> = ({ title, onClick }) => {
  return (
    <div
      onClick={onClick}
      className={`flex-[0.35] rounded-xl ${SURFACE_CARD} ${SURFACE_CARD_HOVER} px-3 py-1.5 flex items-center justify-between cursor-pointer transition-all group select-none`}
    >
      <div className="flex items-center gap-2.5 min-w-0 pr-2">
        <div className="p-1 rounded-lg bg-sky-400/10 text-sky-400 shrink-0">
          <Layers className="w-3.5 h-3.5" />
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-[9px] text-slate-500 font-medium uppercase tracking-wider">
            Dernière fiche
          </span>
          <p className="text-xs text-slate-200 font-medium truncate">
            {title || 'Tampon cognitif vide'}
          </p>
        </div>
      </div>
      <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-sky-300 group-hover:translate-x-0.5 transition-all shrink-0" />
    </div>
  );
};

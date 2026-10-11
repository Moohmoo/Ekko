import React, { useEffect } from 'react';
import { Mascot } from '../home/Mascot';
import { useViewStore } from '../../core/stores/useViewStore';
import { WELCOME_DURATION_MS } from '../../design-system/tokens';

export const WelcomeView: React.FC = () => {
  const setViewMode = useViewStore((state) => state.setViewMode);

  useEffect(() => {
    const timer = setTimeout(() => {
      setViewMode('home');
    }, WELCOME_DURATION_MS);

    return () => clearTimeout(timer);
  }, [setViewMode]);

  return (
    <div className="w-full h-full flex items-center justify-center select-none relative overflow-hidden">
      {/* Soft background ambient glow */}
      <div className="absolute inset-0 bg-radial from-sky-400/[0.08] via-transparent to-transparent pointer-events-none" />

      {/* Mascot alone at the center, waving hello with right hand */}
      <div className="flex items-center justify-center">
        <Mascot emotion="welcome" />
      </div>
    </div>
  );
};

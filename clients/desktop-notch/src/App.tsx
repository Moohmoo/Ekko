import React, { useState } from 'react';
import { Sparkles, Terminal } from 'lucide-react';

export const App: React.FC = () => {
  const [active, setActive] = useState<boolean>(false);

  return (
    <div className="flex items-center justify-between h-8 px-3 rounded-full bg-neutral-900/90 text-white text-xs border border-white/10 backdrop-blur shadow-lg">
      <div
        className="flex items-center gap-1.5 cursor-pointer"
        onClick={() => setActive(!active)}
      >
        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
        <span className="font-semibold tracking-wide">Ekko</span>
      </div>
      <div className="flex items-center gap-1 text-neutral-400">
        <Terminal className="w-3 h-3" />
        <span>{active ? 'Active' : 'Ready'}</span>
      </div>
    </div>
  );
};

export default App;

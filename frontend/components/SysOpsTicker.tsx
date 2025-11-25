
import React from 'react';

interface SysOpsTickerProps {
  logs: string[];
}

export const SysOpsTicker: React.FC<SysOpsTickerProps> = ({ logs }) => {
  return (
    <div className="w-full bg-void border-t border-white/10 h-6 overflow-hidden flex items-center relative z-50 select-none">
      {/* Label */}
      <div className="bg-cyan/10 text-cyan px-2 h-full flex items-center text-[10px] font-mono font-bold shrink-0 border-r border-cyan/20 z-10">
         SYS_OPS_LOG
      </div>
      
      {/* Marquee Container */}
      <div className="flex-1 overflow-hidden relative h-full">
         <div className="absolute whitespace-nowrap animate-marquee flex items-center h-full">
            {/* Duplicate logs to ensure smooth loop if content is short, 
                or just map them. For a true marquee, CSS usually requires duplicating content 
                or ensuring it's wider than screen. Here we map logs joined. */}
            
            <div className="flex gap-8 px-4">
              {[...logs, ...logs].map((log, i) => ( // Duplicate once for effect
                 <span key={i} className="text-[10px] font-mono text-green-500/80 flex items-center gap-2">
                    <span className="opacity-50">[{new Date().toLocaleTimeString()}]</span>
                    {log}
                 </span>
              ))}
            </div>
         </div>
      </div>
      
      {/* Right side status */}
      <div className="bg-black text-gray-500 px-2 h-full flex items-center text-[9px] font-mono shrink-0 border-l border-white/10 z-10">
         LIVE_FEED
      </div>

      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
        .animate-marquee:hover {
          animation-play-state: paused;
        }
      `}</style>
    </div>
  );
};

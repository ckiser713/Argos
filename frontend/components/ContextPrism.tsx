
import React, { useState } from 'react';
import { X, FileText, GitBranch, MessageSquare, Database } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export interface ContextItem {
  id: string;
  name: string;
  type: 'pdf' | 'repo' | 'chat';
  tokens: number;
}

interface ContextPrismProps {
  items: ContextItem[];
  totalCapacity: number; // e.g., 128000
  onEject: (id: string) => void;
}

export const ContextPrism: React.FC<ContextPrismProps> = ({ 
  items, 
  totalCapacity, 
  onEject 
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const totalUsed = items.reduce((acc, item) => acc + item.tokens, 0);
  const freeTokens = totalCapacity - totalUsed;

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'pdf': return 'bg-cyan shadow-[0_0_10px_rgba(0,240,255,0.5)]';
      case 'repo': return 'bg-amber shadow-[0_0_10px_rgba(255,191,0,0.5)]';
      case 'chat': return 'bg-purple shadow-[0_0_10px_rgba(189,0,255,0.5)]';
      default: return 'bg-gray-500';
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
        case 'pdf': return <FileText size={12} className="text-cyan" />;
        case 'repo': return <GitBranch size={12} className="text-amber" />;
        case 'chat': return <MessageSquare size={12} className="text-purple" />;
        default: return <Database size={12} />;
    }
  };

  return (
    <div className="w-full bg-black/80 border-t border-white/10 backdrop-blur-md px-4 py-2 relative z-40">
      
      {/* Header / Legend */}
      <div className="flex justify-between items-center mb-1 text-[10px] font-mono text-gray-500">
         <div className="flex items-center gap-2">
            <span className="uppercase tracking-widest text-gray-400 font-bold">Context Prism</span>
            <span>{totalUsed.toLocaleString()} / {totalCapacity.toLocaleString()} TOKENS</span>
         </div>
         <div className="flex gap-3">
             <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-cyan"></div> PDF</span>
             <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-amber"></div> REPO</span>
             <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-purple"></div> CHAT</span>
         </div>
      </div>

      {/* The Stacked Bar */}
      <div className="h-4 w-full bg-white/5 rounded-full overflow-hidden flex relative">
         <AnimatePresence mode='popLayout'>
            {items.map((item) => {
               const widthPercent = (item.tokens / totalCapacity) * 100;
               return (
                  <motion.div
                    key={item.id}
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: `${widthPercent}%`, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className={`h-full relative group cursor-pointer border-r border-black/20 hover:brightness-110 transition-all ${getTypeColor(item.type)}`}
                    onMouseEnter={() => setHoveredId(item.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => onEject(item.id)} // Click to eject for quick access
                  >
                     {/* Hover Tooltip (Positioned absolutely relative to the bar segment) */}
                     {hoveredId === item.id && (
                        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-48 bg-gray-900 border border-white/20 rounded-lg p-2 shadow-2xl z-50 pointer-events-none">
                            <div className="flex items-center justify-between mb-1 border-b border-white/10 pb-1">
                               <div className="flex items-center gap-1 text-[10px] font-bold text-white">
                                  {getIcon(item.type)}
                                  <span className="truncate max-w-[100px]">{item.name}</span>
                               </div>
                               <div className="text-[9px] text-gray-400">{item.type.toUpperCase()}</div>
                            </div>
                            <div className="flex justify-between items-center text-[10px] font-mono text-gray-300">
                               <span>Size:</span>
                               <span className="text-white">{(item.tokens / 1000).toFixed(1)}k</span>
                            </div>
                            <div className="mt-1 text-[9px] text-red-400 text-center font-bold">CLICK TO EJECT</div>
                            
                            {/* Little pointer arrow */}
                            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                        </div>
                     )}
                     
                     {/* Eject X icon overlay on hover */}
                     <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
                        <X size={10} className="text-white drop-shadow-md" />
                     </div>
                  </motion.div>
               );
            })}
         </AnimatePresence>
         
         {/* Free Space Indicator */}
         <div 
           className="h-full bg-transparent flex items-center justify-center"
           style={{ width: `${(freeTokens / totalCapacity) * 100}%` }}
         >
            {freeTokens > 10000 && (
                <span className="text-[9px] text-gray-600 font-mono opacity-50 select-none">FREE SPACE</span>
            )}
         </div>
      </div>

    </div>
  );
};

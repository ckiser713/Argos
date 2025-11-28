
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, FileText, GitBranch, MessageSquare, AlertTriangle, Zap, ArrowRight, BrainCircuit, HardHat } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';
import { ScrambleText } from './ScrambleText';

// --- Types ---

export interface ContextLink {
  type: 'pdf' | 'code' | 'chat';
  title: string;
}

export interface DecisionOption {
  id: string;
  label: string;
  summary: string;
  pros: string[];
  cons: string[];
  analysis_complete?: boolean;
  context_links: ContextLink[];
}

export interface DecisionData {
  id: string;
  question: string;
  options: DecisionOption[];
}

interface OptionInspectorProps {
  data: DecisionData | null;
  isOpen: boolean;
  onClose: () => void;
  onContextSelect?: (fileName: string) => void;
  onCommit?: (option: DecisionOption) => void;
}

export const OptionInspector: React.FC<OptionInspectorProps> = ({ 
  data, 
  isOpen, 
  onClose,
  onContextSelect,
  onCommit
}) => {
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const handleRunAnalysis = (optionId: string) => {
    setAnalyzingId(optionId);
    setTimeout(() => setAnalyzingId(null), 2500); // Mock delay
  };

  const getIcon = (type: string) => {
    switch(type) {
      case 'pdf': return <FileText size={12} className="text-cyan"/>;
      case 'code': return <GitBranch size={12} className="text-amber"/>;
      case 'chat': return <MessageSquare size={12} className="text-purple"/>;
      default: return <FileText size={12}/>;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && data && (
        <>
          <motion.div
             initial={{ opacity: 0 }}
             animate={{ opacity: 1 }}
             exit={{ opacity: 0 }}
             onClick={onClose}
             className="absolute inset-0 bg-black/40 backdrop-blur-[2px] z-40"
          />

          <motion.div
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute top-0 right-0 h-full w-[450px] max-w-[90vw] bg-panel/95 backdrop-blur-xl border-l border-amber/30 shadow-[-10px_0_30px_rgba(0,0,0,0.5)] z-50 flex flex-col"
          >
            <div className="p-5 border-b border-white/10 bg-gradient-to-l from-amber/10 to-transparent flex justify-between items-start shrink-0">
               <div>
                  <div className="flex items-center gap-2 mb-2">
                     <AlertTriangle size={16} className="text-amber" />
                     <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-amber">Decision Point Detected</span>
                  </div>
                  <h2 className="text-lg font-bold text-white leading-tight font-mono">
                     <ScrambleText text={data.question} duration={500} />
                  </h2>
               </div>
               <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors p-1">
                  <X size={20} />
               </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar bg-void/30">
               {data.options.map((option, idx) => (
                 <motion.div 
                   key={option.id}
                   initial={{ opacity: 0, y: 20 }}
                   animate={{ opacity: 1, y: 0 }}
                   transition={{ delay: idx * 0.1 }}
                 >
                   <GlassCard variant="primary" className="group border-white/5 hover:border-amber/30 transition-all !p-0 overflow-hidden">
                      <div className="p-4">
                        <div className="flex justify-between items-start mb-3">
                           <div className="flex items-center gap-2">
                              <div className={`w-1.5 h-1.5 rounded-full ${option.analysis_complete ? 'bg-green-500' : 'bg-gray-500'}`}></div>
                              <span className="text-xs font-mono font-bold text-white">{option.label}</span>
                           </div>
                           {option.analysis_complete !== false && (
                              <span className="text-[9px] text-green-500 font-mono flex items-center gap-1">
                                 <CheckCircle size={10} /> ANALYZED
                              </span>
                           )}
                        </div>

                        <p className="text-xs text-gray-400 leading-relaxed mb-4 border-l-2 border-white/10 pl-3">
                           {option.summary}
                        </p>
                        
                        <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                           <div className="text-[9px] uppercase tracking-widest text-gray-500 font-mono mb-2 flex items-center gap-2">
                              <BrainCircuit size={10} /> Supporting Evidence
                           </div>
                           <div className="space-y-1.5">
                              {option.context_links.map((link, i) => (
                                 <button 
                                   key={i} 
                                   onClick={() => onContextSelect?.(link.title)}
                                   className="w-full flex items-center gap-2 p-1.5 rounded hover:bg-white/5 text-left group/link transition-colors"
                                 >
                                    {getIcon(link.type)}
                                    <span className="text-[10px] font-mono text-cyan truncate flex-1 group-hover/link:underline decoration-cyan/30 underline-offset-2">
                                       {link.title}
                                    </span>
                                    <ArrowRight size={10} className="text-gray-600 opacity-0 group-hover/link:opacity-100 -translate-x-2 group-hover/link:translate-x-0 transition-all" />
                                 </button>
                              ))}
                           </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-white/5 flex justify-end">
                           <NeonButton 
                             variant="amber" 
                             className="!text-[9px] !px-3 !py-1.5"
                             onClick={() => handleRunAnalysis(option.id)}
                             icon={analyzingId === option.id ? <Zap size={10} className="animate-spin"/> : <Zap size={10}/>}
                           >
                              {analyzingId === option.id ? 'AGENT_THINKING...' : 'RUN DEEP-READ ANALYSIS'}
                           </NeonButton>
                        </div>
                      </div>
                      
                      {/* Commit Action Footer */}
                      <div className="bg-amber/10 border-t border-amber/30 p-3 mt-2">
                         <NeonButton 
                            variant="primary" 
                            className="!w-full !justify-center !bg-amber hover:!bg-amber/80 !text-black"
                            onClick={() => onCommit?.(option)}
                            icon={<HardHat size={14}/>}
                         >
                           Select & Enforce
                         </NeonButton>
                      </div>
                   </GlassCard>
                 </motion.div>
               ))}
            </div>

            <div className="p-4 border-t border-white/10 bg-black/40 text-center">
               <span className="text-[9px] text-gray-500 font-mono">
                  DECISION_ENGINE_V2 // AWAITING HUMAN INPUT
               </span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

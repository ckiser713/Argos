
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Cpu, Zap, Activity, Server, Database, Anchor } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';
import { ScrambleText } from './ScrambleText';

interface NeuralLinkConfigProps {
  isOpen: boolean;
  onClose: () => void;
}

type RoleType = 'deep_reader' | 'code_expert' | 'strategic_planner';

interface ModelSpec {
  id: string;
  name: string;
  context: string;
  vram: string;
  speed: string;
}

interface RoleConfig {
  id: RoleType;
  label: string;
  icon: React.ReactNode;
  description: string;
  availableModels: ModelSpec[];
}

const ROLES: RoleConfig[] = [
  {
    id: 'deep_reader',
    label: 'DEEP READER',
    icon: <Database size={18} />,
    description: 'Ingests massive PDF/Text datasets for RAG.',
    availableModels: [
      { id: 'qwen-1m', name: 'Qwen 2.5 (1M Context)', context: '1,000k', vram: 'High', speed: 'Slow' },
      { id: 'gemini-pro', name: 'Gemini 1.5 Pro', context: '2,000k', vram: 'Cloud', speed: 'Med' },
      { id: 'claude-opus', name: 'Claude 3 Opus', context: '200k', vram: 'Cloud', speed: 'Slow' },
    ]
  },
  {
    id: 'code_expert',
    label: 'CODE EXPERT',
    icon: <Cpu size={18} />,
    description: 'Specialized in syntax parsing and refactoring.',
    availableModels: [
      { id: 'qwen-coder', name: 'Qwen Coder 32B', context: '32k', vram: 'Med', speed: 'Fast' },
      { id: 'gpt4-turbo', name: 'GPT-4 Turbo', context: '128k', vram: 'Cloud', speed: 'Fast' },
      { id: 'deepseek-v2', name: 'DeepSeek V2', context: '64k', vram: 'Med', speed: 'Fast' },
    ]
  },
  {
    id: 'strategic_planner',
    label: 'STRATEGIC PLANNER',
    icon: <Activity size={18} />,
    description: 'High-level reasoning and task orchestration.',
    availableModels: [
      { id: 'llama3-70b', name: 'Llama 3 (70B)', context: '8k', vram: 'High', speed: 'Med' },
      { id: 'mixtral-8x22', name: 'Mixtral 8x22B', context: '64k', vram: 'High', speed: 'Fast' },
      { id: 'grok-1', name: 'Grok-1 (Quantized)', context: '8k', vram: 'Med', speed: 'Fast' },
    ]
  }
];

export const NeuralLinkConfig: React.FC<NeuralLinkConfigProps> = ({ isOpen, onClose }) => {
  // State to track selected model ID for each role
  const [selections, setSelections] = useState<Record<RoleType, string>>({
    deep_reader: 'qwen-1m',
    code_expert: 'qwen-coder',
    strategic_planner: 'llama3-70b'
  });

  // State to track "connecting" animation status per role
  const [connectionStatus, setConnectionStatus] = useState<Record<RoleType, 'idle' | 'connecting' | 'connected'>>({
    deep_reader: 'connected',
    code_expert: 'connected',
    strategic_planner: 'connected'
  });

  const handleModelChange = (roleId: RoleType, modelId: string) => {
    // 1. Set to connecting (unplug/replug animation)
    setConnectionStatus(prev => ({ ...prev, [roleId]: 'connecting' }));
    setSelections(prev => ({ ...prev, [roleId]: modelId }));

    // 2. Simulate connection delay
    setTimeout(() => {
      setConnectionStatus(prev => ({ ...prev, [roleId]: 'connected' }));
    }, 1200);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[60] flex items-center justify-center p-4 md:p-10"
          >
            {/* Modal Container */}
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-5xl max-h-[90vh] flex flex-col"
            >
               <GlassCard variant="primary" className="flex flex-col h-full !p-0 overflow-hidden shadow-2xl border-cyan/30">
                  
                  {/* Header */}
                  <div className="flex justify-between items-center p-6 border-b border-white/10 bg-black/40">
                     <div className="flex items-center gap-4">
                        <div className="p-3 bg-cyan/10 rounded-lg border border-cyan/30 shadow-neon-cyan">
                           <Server className="text-cyan" size={24} />
                        </div>
                        <div>
                           <h2 className="text-xl font-mono font-bold text-white tracking-widest flex items-center gap-2">
                              NEURAL_LINK_CONFIG <span className="text-[10px] bg-cyan text-black px-1 rounded">V4.0</span>
                           </h2>
                           <p className="text-xs font-mono text-gray-500">SYSTEM_WIDE_MODEL_ORCHESTRATION</p>
                        </div>
                     </div>
                     <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors text-gray-400 hover:text-white">
                        <X size={24} />
                     </button>
                  </div>

                  {/* Content Grid */}
                  <div className="flex-1 overflow-y-auto p-6 bg-void/50 grid grid-cols-1 md:grid-cols-3 gap-6 relative">
                     {/* Background Grid */}
                     <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(rgba(0,240,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.1)_1px,transparent_1px)] bg-[size:40px_40px]"></div>

                     {ROLES.map((role) => {
                        const currentModelId = selections[role.id];
                        const currentModel = role.availableModels.find(m => m.id === currentModelId);
                        const status = connectionStatus[role.id];
                        const isConnected = status === 'connected';

                        return (
                           <div 
                              key={role.id}
                              className={`
                                 relative group flex flex-col h-full min-h-[320px] rounded-xl border-2 transition-all duration-500 bg-black/60 backdrop-blur-md overflow-hidden
                                 ${isConnected ? 'border-cyan/40 shadow-[0_0_20px_rgba(0,240,255,0.1)]' : 'border-white/10 opacity-80'}
                              `}
                           >
                              {/* Card Header */}
                              <div className="p-4 border-b border-white/5 bg-white/5 flex justify-between items-start">
                                 <div className="flex items-center gap-2 text-cyan">
                                    {role.icon}
                                    <span className="font-mono font-bold text-sm tracking-wider">{role.label}</span>
                                 </div>
                                 <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-cyan shadow-neon-cyan' : 'bg-red-500 animate-pulse'}`}></div>
                              </div>

                              {/* Card Body */}
                              <div className="p-4 flex-1 flex flex-col gap-4 relative z-10">
                                 <p className="text-xs text-gray-500 font-mono h-8 leading-snug">{role.description}</p>
                                 
                                 {/* Dropdown */}
                                 <div className="relative">
                                    <label className="text-[9px] uppercase tracking-widest text-gray-600 font-mono block mb-1">Select Core Model</label>
                                    <div className="relative group/select">
                                       <select 
                                          value={currentModelId}
                                          onChange={(e) => handleModelChange(role.id, e.target.value)}
                                          className="w-full bg-black border border-white/20 rounded px-3 py-2 text-sm font-mono text-white appearance-none focus:border-cyan focus:outline-none focus:shadow-neon-cyan transition-all cursor-pointer hover:border-white/40"
                                       >
                                          {role.availableModels.map(m => (
                                             <option key={m.id} value={m.id} className="bg-gray-900">{m.name}</option>
                                          ))}
                                       </select>
                                       {/* Custom Arrow */}
                                       <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500 group-hover/select:text-cyan transition-colors">
                                          ▼
                                       </div>
                                    </div>
                                 </div>

                                 {/* Specs Grid */}
                                 <div className="grid grid-cols-3 gap-2 mt-auto">
                                    <SpecBox label="CTX" value={currentModel?.context || '-'} delay={0} />
                                    <SpecBox label="VRAM" value={currentModel?.vram || '-'} delay={100} />
                                    <SpecBox label="SPD" value={currentModel?.speed || '-'} delay={200} />
                                 </div>
                              </div>

                              {/* Cable Animation Area */}
                              <div className="h-24 relative bg-black border-t border-white/10 mt-auto overflow-hidden">
                                 <div className="absolute inset-0 flex items-center justify-center">
                                    <CableAnimation status={status} />
                                 </div>
                                 {/* Status Text overlay */}
                                 <div className="absolute bottom-2 right-2 text-[9px] font-mono text-gray-600">
                                    LINK_STATUS: <span className={isConnected ? 'text-cyan' : 'text-amber'}>{status.toUpperCase()}</span>
                                 </div>
                              </div>

                           </div>
                        );
                     })}
                  </div>

                  {/* Footer Actions */}
                  <div className="p-6 border-t border-white/10 bg-black/40 flex justify-end gap-4">
                     <NeonButton variant="amber" onClick={onClose} className="opacity-80 hover:opacity-100">CANCEL</NeonButton>
                     <NeonButton variant="cyan" onClick={onClose} icon={<Zap size={16}/>}>APPLY_CONFIGURATION</NeonButton>
                  </div>

               </GlassCard>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// --- Sub Components ---

const SpecBox = ({ label, value, delay }: { label: string, value: string, delay: number }) => (
   <div className="bg-white/5 border border-white/10 rounded p-2 flex flex-col items-center justify-center">
      <span className="text-[9px] text-gray-500 font-mono uppercase">{label}</span>
      <span className="text-xs font-mono font-bold text-white mt-1">
         <ScrambleText text={value} duration={600} />
      </span>
   </div>
);

const CableAnimation = ({ status }: { status: 'idle' | 'connecting' | 'connected' }) => {
   // Calculate X positions based on status
   // Disconnected: Plug is far left (-50), Socket is right (50)
   // Connected: Plug moves to Socket (approx 30)
   
   const isConnected = status === 'connected';
   
   return (
      <div className="relative w-full h-full flex items-center justify-center">
         {/* Socket (Right Side) */}
         <motion.div 
            className="absolute"
            style={{ x: 40 }}
         >
            <div className={`w-8 h-8 rounded-full border-4 flex items-center justify-center transition-colors duration-500 ${isConnected ? 'border-cyan bg-cyan/20 shadow-neon-cyan' : 'border-gray-700 bg-gray-900'}`}>
               <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-white' : 'bg-black'}`}></div>
            </div>
         </motion.div>

         {/* Plug (Moving Part) */}
         <motion.div
            className="absolute flex items-center"
            initial={{ x: -60 }}
            animate={{ x: isConnected ? 24 : -60 }} // 24 aligns plug tip with socket center
            transition={{ type: "spring", stiffness: 60, damping: 12 }}
         >
            {/* Cable Line */}
            <div className={`h-1 w-20 rounded-l-full transition-colors duration-500 ${isConnected ? 'bg-cyan shadow-[0_0_10px_cyan]' : 'bg-gray-700'}`}></div>
            
            {/* Plug Head */}
            <div className={`w-6 h-5 rounded-r-md border-y border-r transition-colors duration-500 flex items-center justify-center ${isConnected ? 'bg-cyan/10 border-cyan' : 'bg-gray-800 border-gray-600'}`}>
               <Anchor size={12} className={`transform -rotate-90 ${isConnected ? 'text-cyan' : 'text-gray-500'}`} />
            </div>
         </motion.div>

         {/* Spark Effect on Connect */}
         <AnimatePresence>
            {isConnected && (
               <motion.div
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: [0, 1, 0], scale: [1, 2, 3] }}
                  transition={{ duration: 0.4 }}
                  className="absolute w-10 h-10 border-2 border-white rounded-full"
                  style={{ x: 40 }}
               ></motion.div>
            )}
         </AnimatePresence>
      </div>
   );
}

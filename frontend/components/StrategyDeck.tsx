
import React, { useState, useEffect, useRef } from 'react';
import { Lightbulb, Terminal, ArrowRight, BrainCircuit, MessageSquare, Quote, Play } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';
import { ScrambleText } from './ScrambleText';

// --- Types ---

interface ChatLog {
  id: string;
  user: string;
  timestamp: string;
  message: string;
  containsIdeaId?: string; // Links to an idea if this is the source
}

type IdeaType = 'feature' | 'infra' | 'unknown' | 'project';

interface Idea {
  id: string;
  type: IdeaType;
  summary: string;
  sourceContext: string;
  sourceUser: string;
  confidence: number;
}

// --- Mock Data ---

const MOCK_LOGS: ChatLog[] = [
  { id: 'l1', timestamp: 'Oct 24 09:12', user: 'sarah_eng', message: 'API latency is spiking again on the /query endpoint.' },
  { id: 'l2', timestamp: 'Oct 24 09:14', user: 'mike_dev', message: 'Yeah, the vector search is doing a full table scan. We should probably implement HNSW indexing on the Qdrant cluster.', containsIdeaId: 'i1' },
  { id: 'l3', timestamp: 'Oct 24 09:45', user: 'system', message: '[ALERT] Memory usage at 85% on node-04.' },
  { id: 'l4', timestamp: 'Oct 24 10:00', user: 'sarah_eng', message: "Agreed on HNSW. Also, did we ever finish that 'Auto-Tagging' bot? The one that reads commit messages?" },
  { id: 'l5', timestamp: 'Oct 24 10:05', user: 'mike_dev', message: 'Nah, abandoned it. But honestly, we should build a tool that generates PR descriptions from diffs automatically. Would save so much time.', containsIdeaId: 'i2' },
  { id: 'l6', timestamp: 'Oct 24 10:10', user: 'sarah_eng', message: 'Lets put that on the backlog.' },
  { id: 'l7', timestamp: 'Oct 25 14:20', user: 'dave_arch', message: "I'm looking at the ingest pipeline. Eventually, it would be cool if the system could listen to voice meetings and extract tasks directly.", containsIdeaId: 'i3' },
  { id: 'l8', timestamp: 'Oct 25 14:22', user: 'dave_arch', message: 'Just a thought for Q4.' },
];

const EXTRACTED_IDEAS: Idea[] = [
  {
    id: 'i1',
    type: 'infra',
    summary: 'Implement HNSW indexing on Qdrant cluster to resolve vector search latency.',
    sourceContext: "We should probably implement HNSW indexing on the Qdrant cluster.",
    sourceUser: 'mike_dev',
    confidence: 0.95
  },
  {
    id: 'i2',
    type: 'feature',
    summary: 'Automated PR description generator using diff analysis.',
    sourceContext: "build a tool that generates PR descriptions from diffs automatically.",
    sourceUser: 'mike_dev',
    confidence: 0.88
  },
  {
    id: 'i3',
    type: 'project',
    summary: 'Voice-to-Task extraction for engineering meetings.',
    sourceContext: "listen to voice meetings and extract tasks directly.",
    sourceUser: 'dave_arch',
    confidence: 0.72
  }
];

export const StrategyDeck: React.FC = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [visibleLogs, setVisibleLogs] = useState<ChatLog[]>([]);
  const [foundIdeas, setFoundIdeas] = useState<Idea[]>([]);
  const [scanIndex, setScanIndex] = useState(-1);
  const [statusText, setStatusText] = useState('READY_TO_SCAN');

  const scrollRef = useRef<HTMLDivElement>(null);

  // Initial Load of logs
  useEffect(() => {
    // Stagger load logs
    let delay = 0;
    MOCK_LOGS.forEach((log, index) => {
      setTimeout(() => {
        setVisibleLogs(prev => [...prev, log]);
      }, delay);
      delay += 150; // fast typing effect
    });
  }, []);

  // Auto scroll logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleLogs]);

  const runAnalysis = () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setFoundIdeas([]);
    setScanIndex(-1);
    setStatusText('INITIALIZING_STRATEGIST_PERSONA...');

    let currentIndex = 0;
    
    const interval = setInterval(() => {
      if (currentIndex >= MOCK_LOGS.length) {
        clearInterval(interval);
        setIsAnalyzing(false);
        setStatusText('ANALYSIS_COMPLETE');
        setScanIndex(-1);
        return;
      }

      setScanIndex(currentIndex);
      const currentLog = MOCK_LOGS[currentIndex];

      // Visual feedback updates
      if (currentIndex % 2 === 0) setStatusText('READING_STREAM...');
      
      // Check if this log has an idea
      if (currentLog.containsIdeaId) {
        setStatusText('SIGNAL_DETECTED');
        const idea = EXTRACTED_IDEAS.find(i => i.id === currentLog.containsIdeaId);
        if (idea) {
          // Delay the push slightly for effect
          setTimeout(() => {
            setFoundIdeas(prev => [...prev, idea]);
          }, 400);
        }
      }

      currentIndex++;
    }, 800); // Speed of scanning per message
  };

  const getTypeColor = (type: IdeaType) => {
    switch (type) {
      case 'feature': return 'text-cyan border-cyan bg-cyan/10';
      case 'infra': return 'text-amber border-amber bg-amber/10';
      case 'project': return 'text-purple border-purple bg-purple/10';
      default: return 'text-gray-400 border-gray-400';
    }
  };

  return (
    <div className="h-[calc(100vh-140px)] w-full flex gap-6 animate-fade-in pb-4">
      
      {/* LEFT COLUMN: Raw Intelligence */}
      <div className="w-1/2 flex flex-col gap-4">
        <div className="flex justify-between items-end">
           <div>
              <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
                 <Terminal className="text-gray-400" />
                 RAW_INTELLIGENCE
              </h2>
              <p className="text-gray-500 font-mono text-xs mt-1">SOURCE: ENGINEERING_CHAT_LOGS_V2.DB</p>
           </div>
           <NeonButton variant="cyan" onClick={runAnalysis} disabled={isAnalyzing} icon={<Play size={14} />}>
              {isAnalyzing ? 'SCANNING...' : 'RUN_STRATEGY_ANALYSIS'}
           </NeonButton>
        </div>

        <GlassCard variant="void" className="flex-1 !p-0 overflow-hidden relative border-opacity-50">
           {/* Scanline overlay */}
           {isAnalyzing && (
             <div 
               className="absolute left-0 right-0 h-[2px] bg-cyan/50 z-20 shadow-[0_0_15px_cyan]"
               style={{ top: `${(scanIndex / MOCK_LOGS.length) * 100}%`, transition: 'top 0.8s linear' }}
             ></div>
           )}

           <div className="absolute top-2 right-2 z-20">
              <span className={`text-[10px] font-mono font-bold px-2 py-1 rounded bg-black/80 border border-white/10 ${isAnalyzing ? 'text-cyan animate-pulse' : 'text-gray-500'}`}>
                {statusText}
              </span>
           </div>

           <div className="p-4 h-full overflow-y-auto font-mono text-sm space-y-3 scrollbar-hide" ref={scrollRef}>
              {visibleLogs.map((log, index) => {
                const isScanned = index === scanIndex;
                const isPast = index < scanIndex;
                const hasIdea = log.containsIdeaId && (isPast || isScanned);
                
                return (
                  <div 
                    key={log.id} 
                    className={`
                      relative pl-3 py-1 transition-all duration-300
                      ${isScanned ? 'bg-cyan/5 -translate-x-1' : ''}
                      ${hasIdea ? 'border-l-2 border-amber' : 'border-l-2 border-transparent'}
                    `}
                  >
                     <div className="flex items-baseline gap-2 text-xs text-gray-500 mb-0.5">
                        <span>{log.timestamp}</span>
                        <span className={`font-bold ${hasIdea ? 'text-amber' : 'text-gray-400'}`}>@{log.user}</span>
                     </div>
                     <div className={`text-gray-300 ${isScanned ? 'text-white' : ''}`}>
                        {log.message}
                     </div>
                  </div>
                );
              })}
              {visibleLogs.length === 0 && (
                <div className="text-center text-gray-600 mt-20">LOADING_LOGS...</div>
              )}
           </div>
        </GlassCard>
      </div>

      {/* RIGHT COLUMN: Extracted Ideas */}
      <div className="w-1/2 flex flex-col gap-4">
        <div>
           <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
              <BrainCircuit className="text-purple" />
              STRATEGIC_INSIGHTS
           </h2>
           <p className="text-gray-500 font-mono text-xs mt-1">PERSONA: CHIEF_TECHNICAL_STRATEGIST</p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
           {foundIdeas.length === 0 && !isAnalyzing && (
              <div className="h-64 flex flex-col items-center justify-center border border-dashed border-white/10 rounded-xl bg-white/5 text-gray-500 gap-4">
                 <Lightbulb size={32} className="opacity-50" />
                 <div className="text-center">
                   <div className="text-sm font-mono">NO_IDEAS_EXTRACTED</div>
                   <div className="text-xs mt-1">Run analysis to mine chat logs for value.</div>
                 </div>
              </div>
           )}

           {foundIdeas.map((idea, idx) => (
             <div key={idea.id} className="animate-fade-in-up" style={{ animationDelay: `${idx * 100}ms` }}>
                <GlassCard variant="primary" className="group hover:border-cyan/50 transition-colors">
                   <div className="flex justify-between items-start mb-3">
                      <div className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getTypeColor(idea.type)}`}>
                        {idea.type}
                      </div>
                      <div className="text-[10px] font-mono text-gray-500 flex items-center gap-1">
                         CONFIDENCE: <span className="text-white">{(idea.confidence * 100).toFixed(0)}%</span>
                      </div>
                   </div>

                   <h3 className="text-lg font-bold text-white mb-4 leading-snug">
                     <ScrambleText text={idea.summary} duration={600} />
                   </h3>

                   <div className="bg-black/40 rounded p-3 border border-white/5 relative">
                      <Quote size={12} className="absolute top-2 left-2 text-gray-600" />
                      <p className="text-xs text-gray-400 font-mono italic pl-4">
                        "{idea.sourceContext}"
                      </p>
                      <div className="mt-2 text-[10px] text-gray-600 text-right font-mono">
                        — @{idea.sourceUser}
                      </div>
                   </div>

                   <div className="mt-4 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="flex items-center gap-2 text-xs font-mono text-cyan hover:text-white transition-colors">
                         CONVERT_TO_TICKET <ArrowRight size={12} />
                      </button>
                   </div>
                </GlassCard>
             </div>
           ))}
        </div>
      </div>

    </div>
  );
};

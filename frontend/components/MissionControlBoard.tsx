
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  GitBranch, 
  MessageSquare, 
  FileText, 
  MoreHorizontal, 
  Layers, 
  Zap, 
  CheckCircle, 
  AlertTriangle, 
  Database,
  ArrowRight,
  Bot
} from 'lucide-react';
import { GlassCard } from './GlassCard';
import { ScrambleText } from './ScrambleText';

// --- Types ---

type OriginType = 'repo' | 'chat' | 'pdf';
type ColumnId = 'backlog' | 'todo' | 'in_progress' | 'done';

interface ContextFile {
  name: string;
  type: 'code' | 'doc';
}

interface Task {
  id: string;
  title: string;
  origin: OriginType;
  confidence: number; // 0-100
  column: ColumnId;
  context: ContextFile[];
  priority: 'high' | 'medium' | 'low';
}

// --- Mock Data ---

const INITIAL_TASKS: Task[] = [
  {
    id: 't1',
    title: 'Refactor Auth Middleware',
    origin: 'repo',
    confidence: 92,
    column: 'backlog',
    context: [{ name: 'auth_core.rs', type: 'code' }, { name: 'user_session.ts', type: 'code' }],
    priority: 'high'
  },
  {
    id: 't2',
    title: 'Vector Search Integration',
    origin: 'chat',
    confidence: 88,
    column: 'todo',
    context: [{ name: 'search_logic.py', type: 'code' }, { name: 'rag_spec.pdf', type: 'doc' }],
    priority: 'medium'
  },
  {
    id: 't3',
    title: 'Memory Leak Analysis',
    origin: 'pdf',
    confidence: 99,
    column: 'in_progress',
    context: [{ name: 'heap_dump_v2.log', type: 'doc' }, { name: 'allocator.cpp', type: 'code' }],
    priority: 'high'
  },
  {
    id: 't4',
    title: 'Update Neural Weights',
    origin: 'repo',
    confidence: 75,
    column: 'backlog',
    context: [{ name: 'model_config.json', type: 'code' }],
    priority: 'low'
  },
  {
    id: 't5',
    title: 'Deploy to Sector 7',
    origin: 'chat',
    confidence: 100,
    column: 'done',
    context: [{ name: 'deploy_manifest.yaml', type: 'code' }],
    priority: 'medium'
  }
];

const COLUMNS: { id: ColumnId; label: string; color: string }[] = [
  { id: 'backlog', label: 'DETECTED_GAPS', color: 'border-white/20' },
  { id: 'todo', label: 'ACTIVE_PROTOCOLS', color: 'border-cyan/50' },
  { id: 'in_progress', label: 'COMPILING', color: 'border-purple/50' },
  { id: 'done', label: 'DEPLOYED', color: 'border-green-500/50' },
];

export const MissionControlBoard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>(INITIAL_TASKS);
  const [isDragging, setIsDragging] = useState(false);
  const [chatDropActive, setChatDropActive] = useState(false);
  const [showAiPrompt, setShowAiPrompt] = useState<{ visible: boolean; taskTitle: string } | null>(null);

  // Drag handlers
  const handleDragStart = () => {
    setIsDragging(true);
  };

  const handleDragEnd = (event: any, info: any, task: Task) => {
    setIsDragging(false);
    setChatDropActive(false);

    // Check if dropped in Chat Zone (right side of screen roughly)
    if (info.point.x > window.innerWidth - 300) {
       triggerAiPrompt(task);
    }
  };

  const triggerAiPrompt = (task: Task) => {
    setShowAiPrompt({ visible: true, taskTitle: task.title });
    setTimeout(() => setShowAiPrompt(null), 4000);
  };

  return (
    <div className="h-[calc(100vh-140px)] w-full relative overflow-hidden flex flex-col perspective-[2000px]">
      
      {/* Header */}
      <div className="flex justify-between items-end mb-6 shrink-0 relative z-10">
        <div>
          <h2 className="text-2xl font-mono text-white tracking-wide flex items-center gap-3">
             <Layers className="text-cyan" />
             MISSION_CONTROL
          </h2>
          <p className="text-gray-500 font-mono text-xs mt-1">CONTEXT-AWARE TASK ORCHESTRATION</p>
        </div>
        <div className="flex items-center gap-4">
           <div className="flex items-center gap-2 text-xs font-mono text-gray-400 bg-white/5 px-3 py-1 rounded-full border border-white/10">
              <div className="w-2 h-2 rounded-full bg-cyan animate-pulse"></div>
              AUTONOMOUS_MODE: ON
           </div>
        </div>
      </div>

      {/* 3D Tilted Board Container */}
      <div 
        className="flex-1 overflow-x-auto overflow-y-hidden pb-4 px-4"
        style={{ transformStyle: 'preserve-3d' }}
      >
        <div 
           className="flex gap-6 h-full min-w-max transition-transform duration-700 ease-out origin-top"
           style={{ transform: 'rotateX(5deg) scale(0.98)' }}
        >
          {COLUMNS.map(col => (
            <div key={col.id} className="w-80 flex flex-col gap-4 group">
               {/* Column Header */}
               <div className={`
                 flex items-center justify-between p-3 rounded-t-lg bg-panel/80 backdrop-blur border-b-2 ${col.color}
                 shadow-[0_10px_30px_-10px_rgba(0,0,0,0.5)]
               `}>
                  <span className="font-mono text-xs font-bold tracking-widest text-gray-300">{col.label}</span>
                  <span className="text-[10px] font-mono text-gray-500 bg-black/50 px-2 py-0.5 rounded">
                     {tasks.filter(t => t.column === col.id).length}
                  </span>
               </div>

               {/* Column Track */}
               <div className="flex-1 rounded-b-lg bg-white/5 border border-white/5 p-3 space-y-3 overflow-y-auto scrollbar-hide relative">
                  {/* Grid Lines Overlay */}
                  <div className="absolute inset-0 opacity-10 pointer-events-none" 
                       style={{ backgroundImage: 'linear-gradient(0deg, transparent 24%, rgba(255, 255, 255, .05) 25%, rgba(255, 255, 255, .05) 26%, transparent 27%, transparent 74%, rgba(255, 255, 255, .05) 75%, rgba(255, 255, 255, .05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(255, 255, 255, .05) 25%, rgba(255, 255, 255, .05) 26%, transparent 27%, transparent 74%, rgba(255, 255, 255, .05) 75%, rgba(255, 255, 255, .05) 76%, transparent 77%, transparent)', backgroundSize: '50px 50px' }}>
                  </div>

                  {tasks.filter(t => t.column === col.id).map(task => (
                     <KanbanCard 
                       key={task.id} 
                       task={task} 
                       onDragStart={handleDragStart}
                       onDragEnd={handleDragEnd}
                     />
                  ))}
                  
                  {/* Empty State placeholder */}
                  {tasks.filter(t => t.column === col.id).length === 0 && (
                     <div className="h-24 border-2 border-dashed border-white/5 rounded flex items-center justify-center">
                        <span className="text-xs font-mono text-gray-600">NO_DATA</span>
                     </div>
                  )}
               </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Drop Zone Overlay */}
      <AnimatePresence>
         {isDragging && (
           <motion.div
             initial={{ x: 300, opacity: 0 }}
             animate={{ x: 0, opacity: 1 }}
             exit={{ x: 300, opacity: 0 }}
             className={`
                absolute top-20 bottom-20 right-0 w-64 rounded-l-2xl border-l-2 border-y-2 border-dashed border-purple/50 bg-black/80 backdrop-blur-xl z-50
                flex flex-col items-center justify-center p-6 text-center
                ${chatDropActive ? 'bg-purple/20 border-purple shadow-neon-purple' : ''}
             `}
             onMouseEnter={() => setChatDropActive(true)}
             onMouseLeave={() => setChatDropActive(false)}
           >
              <div className="p-4 rounded-full bg-purple/20 text-purple mb-4 animate-bounce">
                 <Bot size={32} />
              </div>
              <h3 className="font-mono font-bold text-white text-sm mb-2">INITIATE_PROTOCOL</h3>
              <p className="text-xs text-gray-400 font-mono">Drop card here to load context and start AI agent task.</p>
           </motion.div>
         )}
      </AnimatePresence>

      {/* AI Prompt Notification */}
      <AnimatePresence>
         {showAiPrompt && (
           <motion.div
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 50, opacity: 0 }}
              className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-panel border border-cyan/30 shadow-neon-cyan px-6 py-4 rounded-xl flex items-center gap-4 z-50 max-w-lg"
           >
              <div className="relative">
                 <div className="absolute inset-0 bg-cyan blur-lg opacity-50 animate-pulse"></div>
                 <Bot className="text-cyan relative z-10" />
              </div>
              <div>
                 <div className="text-xs text-cyan font-mono font-bold uppercase tracking-wider mb-1">AI Agent Activation</div>
                 <div className="text-sm text-white">
                    Processing <span className="text-cyan font-bold">{showAiPrompt.taskTitle}</span>. <br/>
                    <span className="text-gray-400 text-xs">Loaded 3 context files. Generating execution plan...</span>
                 </div>
              </div>
           </motion.div>
         )}
      </AnimatePresence>

    </div>
  );
};

// --- Sub-components ---

interface KanbanCardProps {
  task: Task;
  onDragStart: () => void;
  onDragEnd: (e: any, info: any, t: Task) => void;
}

const KanbanCard: React.FC<KanbanCardProps> = ({ task, onDragStart, onDragEnd }) => {
  const [showContext, setShowContext] = useState(false);

  const getOriginIcon = (origin: OriginType) => {
     switch(origin) {
        case 'repo': return <GitBranch size={12} />;
        case 'chat': return <MessageSquare size={12} />;
        case 'pdf': return <FileText size={12} />;
     }
  };

  const getPriorityColor = (p: string) => {
     switch(p) {
        case 'high': return 'text-amber';
        case 'medium': return 'text-cyan';
        default: return 'text-gray-500';
     }
  };

  return (
    <motion.div
       layout
       drag
       dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }} // Constraints are loose to allow dragging to drop zone
       dragElastic={0.2}
       onDragStart={onDragStart}
       onDragEnd={(e, info) => onDragEnd(e, info, task)}
       whileHover={{ scale: 1.02, rotateZ: -1, zIndex: 10 }}
       whileDrag={{ scale: 1.1, cursor: 'grabbing', zIndex: 50 }}
       className="relative group cursor-grab active:cursor-grabbing"
    >
       <GlassCard 
         variant={task.origin === 'repo' ? 'amber' : task.origin === 'chat' ? 'purple' : 'cyan'} 
         className="!p-0 overflow-visible"
       >
          <div className="p-3 relative bg-black/40 backdrop-blur-sm rounded-xl">
             
             {/* Header */}
             <div className="flex justify-between items-start mb-2">
                <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] uppercase font-mono border border-white/5 bg-white/5 ${task.origin === 'repo' ? 'text-amber' : task.origin === 'chat' ? 'text-purple' : 'text-cyan'}`}>
                   {getOriginIcon(task.origin)}
                   <span>{task.origin.toUpperCase()}</span>
                </div>
                <button className="text-gray-500 hover:text-white"><MoreHorizontal size={14}/></button>
             </div>

             {/* Title */}
             <h4 className="text-sm font-bold text-gray-200 mb-3 leading-snug">{task.title}</h4>

             {/* Metrics / Footer */}
             <div className="flex items-center justify-between border-t border-white/5 pt-2 mt-2">
                
                {/* Confidence Gauge */}
                <div className="flex items-center gap-2 group/tooltip relative">
                   <div className="relative w-5 h-5">
                      <svg className="w-full h-full -rotate-90">
                         <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="2" fill="transparent" className="text-gray-700" />
                         <circle 
                           cx="10" cy="10" r="8" 
                           stroke="currentColor" 
                           strokeWidth="2" 
                           fill="transparent" 
                           strokeDasharray={50} 
                           strokeDashoffset={50 - (50 * task.confidence) / 100} 
                           className={task.confidence > 90 ? 'text-green-500' : 'text-amber'}
                         />
                      </svg>
                   </div>
                   <span className="text-[10px] font-mono text-gray-400">{task.confidence}%</span>
                </div>

                {/* Context Payload Button */}
                <div 
                  className="relative"
                  onMouseEnter={() => setShowContext(true)}
                  onMouseLeave={() => setShowContext(false)}
                >
                   <button className="flex items-center gap-1.5 text-[10px] font-mono text-cyan hover:bg-cyan/10 px-2 py-1 rounded transition-colors">
                      <Database size={10} />
                      PAYLOAD
                   </button>

                   {/* Context Hover Tooltip */}
                   <AnimatePresence>
                     {showContext && (
                        <motion.div
                           initial={{ opacity: 0, y: 10, scale: 0.9 }}
                           animate={{ opacity: 1, y: 0, scale: 1 }}
                           exit={{ opacity: 0, scale: 0.9 }}
                           className="absolute bottom-full right-0 mb-2 w-48 bg-gray-900/95 backdrop-blur-xl border border-cyan/30 rounded-lg p-3 shadow-2xl z-50 pointer-events-none"
                        >
                           <div className="text-[9px] uppercase tracking-widest text-cyan mb-2 font-bold flex items-center gap-1">
                              <Zap size={10} /> Context Files
                           </div>
                           <div className="space-y-1">
                              {task.context.map((ctx, idx) => (
                                 <div key={idx} className="flex items-center gap-2 text-[10px] text-gray-300">
                                    {ctx.type === 'code' ? <GitBranch size={8} className="text-amber"/> : <FileText size={8} className="text-cyan"/>}
                                    <span className="truncate">{ctx.name}</span>
                                 </div>
                              ))}
                           </div>
                           <div className="mt-2 pt-2 border-t border-white/10 text-[9px] text-gray-500 font-mono text-center">
                              DRAG TO CHAT TO PROCESS
                           </div>
                        </motion.div>
                     )}
                   </AnimatePresence>
                </div>

             </div>
          </div>
       </GlassCard>
    </motion.div>
  );
};

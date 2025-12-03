import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
   GitBranch, MessageSquare, FileText, MoreHorizontal, Layers, CheckCircle, Bot, X, Terminal, GitPullRequest, Code,
} from 'lucide-react';
import { GlassCard } from './GlassCard';
import { useIdeas } from '../src/hooks/useIdeas';
import { useCurrentProject } from '@src/hooks/useProjects';
import { ErrorDisplay } from '../src/components/ErrorDisplay';
import { NeonButton } from './NeonButton';

// --- Types ---
type OriginType = 'repo' | 'chat' | 'pdf';
type ColumnId = 'backlog' | 'todo' | 'in_progress' | 'done';
type TaskStatus = 'idle' | 'delegated' | 'complete' | 'error';

interface Task {
   id: string;
   title: string;
   origin: OriginType;
   column: ColumnId;
   priority: 'high' | 'medium' | 'low';
   status: TaskStatus;
   agentLogs?: string[];
}

// Uses real API data from useIdeas hook
const useMissionControlTasks = () => {
   const { project } = useCurrentProject();
   const { data: ideasData, isLoading, error, refetch } = useIdeas({ projectId: project?.id, status: 'active' });

   const tasks: Task[] = (ideasData?.items || []).map(ticket => ({
      id: ticket.id,
      title: ticket.title,
      origin: 'chat',
      column: ticket.status === 'done' ? 'done' : 'backlog',
      priority: ticket.priority || 'medium',
      status: ticket.status === 'done' ? 'complete' : 'idle',
      // TODO: Fetch real agent logs from agent runs API when available
      agentLogs: undefined,
   }));

   return { tasks, isLoading, error, refetch };
};

const COLUMNS: { id: ColumnId; label: string }[] = [
   { id: 'backlog', label: 'DETECTED_GAPS' },
   { id: 'todo', label: 'ACTIVE_PROTOCOLS' },
   { id: 'in_progress', label: 'AGENT_EXECUTING' },
   { id: 'done', label: 'COMMITTED' },
];

const AGENTS = [
    { id: 'coder-1', name: 'Coder Agent', specialization: 'TypeScript/Python' },
    { id: 'arch-1', name: 'Architect Agent', specialization: 'System Design' },
];

// --- Sub-components ---

const AgentLog = ({ logs }: { logs: string[] }) => (
  <div className="mt-2 p-2 bg-black/70 rounded border border-white/10 h-24 overflow-y-auto font-mono text-xs custom-scrollbar">
    {logs.map((log, i) => (
      <div key={i} className="flex items-start">
        <span className="text-cyan mr-2">&gt;</span>
        <span className="text-gray-300 break-words">{log}</span>
      </div>
    ))}
  </div>
);

const DiffViewer = ({ onClose }: { onClose: () => void }) => (
    <motion.div initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
        <motion.div initial={{scale: 0.9}} animate={{scale: 1}} exit={{scale: 0.9}} className="w-full max-w-4xl h-[80vh] bg-panel border border-white/20 rounded-xl flex flex-col" onClick={e => e.stopPropagation()}>
            <header className="p-4 border-b border-white/10 flex justify-between items-center">
                <h3 className="font-mono text-white flex items-center gap-2"><GitPullRequest /> Review Diff</h3>
                <NeonButton onClick={onClose} icon={<X size={16}/>} />
            </header>
            <div className="flex-1 p-4 font-mono text-sm overflow-y-auto custom-scrollbar">
                <div className="text-gray-400">--- a/src/api/users.ts</div>
                <div className="text-gray-400">+++ b/src/api/users.ts</div>
                <div className="text-cyan">@@ -10,5 +10,15 @@</div>
                <div> import {'{'} User {'}'} from './models';</div>
                <div className="text-green-500">+import {'{'} UserProfile {'}'} from './models';</div>
                <div className="text-red-500">-router.get('/users/:id', (req, res) =&gt; {'{'}</div>
                <div className="text-green-500">+router.get('/users/:id/profile', (req, res) =&gt; {'{'}</div>
                <div>   const user = await db.findUser(req.params.id);</div>
                <div className="text-green-500">+  const profile = await db.findProfile(req.params.id);</div>
                <div>   res.json(user);</div>
                <div className="text-green-500">+  res.json({'{'}...user, ...profile{'}'});</div>
                <div> {'}'}</div>
            </div>
        </motion.div>
    </motion.div>
);

const KanbanCard = ({ task, onDragStart }: { task: Task, onDragStart: (e: React.DragEvent, taskId: string) => void }) => {
    const [showDiff, setShowDiff] = useState(false);

    return (
        <>
            <motion.div
                layout
                draggable
                onDragStart={(e) => onDragStart(e as unknown as React.DragEvent, task.id)}
                whileHover={{ scale: 1.03 }}
                whileDrag={{ scale: 1.1, zIndex: 50, cursor: 'grabbing' }}
                className="relative group cursor-grab"
            >
                <GlassCard variant="primary" className="!p-3">
                    <h4 className="text-sm font-bold text-gray-200 mb-2">{task.title}</h4>
                    {task.status === 'delegated' && task.agentLogs && <AgentLog logs={task.agentLogs} />}
                    <div className="flex justify-between items-center mt-2">
                        <div className="flex items-center gap-2">
                            <div className={`px-2 py-0.5 rounded text-[10px] font-mono border ${task.origin === 'repo' ? 'text-amber border-amber' : 'text-cyan border-cyan'}`}>{task.origin}</div>
                            <div className={`px-2 py-0.5 rounded text-[10px] font-mono border ${task.priority === 'high' ? 'text-red-500 border-red-500' : 'text-gray-400 border-gray-400'}`}>{task.priority}</div>
                        </div>
                        {task.status === 'complete' && (
                            <NeonButton onClick={() => setShowDiff(true)} variant="secondary" className="text-xs !px-2 !py-1" icon={<Code size={14} />}>
                                Review Diff
                            </NeonButton>
                        )}
                    </div>
                </GlassCard>
            </motion.div>
            <AnimatePresence>{showDiff && <DiffViewer onClose={() => setShowDiff(false)} />}</AnimatePresence>
        </>
    );
};

export const MissionControlBoard: React.FC = () => {
   const { tasks: initialTasks, isLoading, error, refetch } = useMissionControlTasks();
   const [tasks, setTasks] = useState<Task[]>([]);
   const [draggedTaskId, setDraggedTaskId] = useState<string | null>(null);
   const [delegationModal, setDelegationModal] = useState<{ visible: boolean; task?: Task; agent?: typeof AGENTS[0] }>({ visible: false });

   useEffect(() => {
       if (initialTasks) setTasks(initialTasks);
   }, [initialTasks]);

   const handleDragStart = (e: React.DragEvent, taskId: string) => {
       setDraggedTaskId(taskId);
       e.dataTransfer.effectAllowed = 'move';
   };
   
   const handleDropOnAgent = (agent: typeof AGENTS[0]) => {
       if (!draggedTaskId) return;
       const task = tasks.find(t => t.id === draggedTaskId);
       if (task) {
           setDelegationModal({ visible: true, task, agent });
       }
       setDraggedTaskId(null);
   };
   
   const confirmDelegation = () => {
       if (!delegationModal.task) return;
       const { task } = delegationModal;
       setTasks(currentTasks => currentTasks.map(t => 
           t.id === task.id ? { ...t, column: 'in_progress', status: 'delegated', agentLogs: ["Agent accepted task. Reading context..."] } : t
       ));
       
       // Simulate agent logs
       let logCount = 0;
       const interval = setInterval(() => {
           logCount++;
           const newLog = `Processing step ${logCount}...`;
           setTasks(currentTasks => currentTasks.map(t =>
               t.id === task.id ? { ...t, agentLogs: [...(t.agentLogs || []), newLog] } : t
           ));
           if(logCount > 4) {
               clearInterval(interval);
               setTasks(currentTasks => currentTasks.map(t => 
                 t.id === task.id ? { ...t, column: 'done', status: 'complete', agentLogs: [...(t.agentLogs || []), 'Task complete. Commit pushed.'] } : t
               ));
           }
       }, 1500);

       setDelegationModal({ visible: false });
   };

   if (isLoading) return <div className="text-gray-400 font-mono">Loading Mission Control...</div>;
   if (error) return <div className="p-6"><ErrorDisplay error={error} onRetry={refetch} title="Failed to load tasks" /></div>;

   return (
      <>
        <div className="h-[calc(100vh-140px)] w-full relative overflow-hidden flex flex-col">
            <div className="flex justify-between items-end mb-4 shrink-0">
                <h2 className="text-2xl font-mono text-white tracking-wide flex items-center gap-3"><Layers className="text-cyan" />MISSION_CONTROL</h2>
            </div>

            <div className="flex-1 grid grid-cols-4 gap-4 overflow-x-auto pb-4">
                {COLUMNS.map(col => (
                    <div key={col.id} className="bg-black/20 rounded-lg flex flex-col">
                        <div className="p-3 border-b-2 border-white/10">
                            <span className="font-mono text-xs font-bold tracking-widest text-gray-300">{col.label} ({tasks.filter(t => t.column === col.id).length})</span>
                        </div>
                        <div className="p-3 space-y-3 overflow-y-auto flex-1 custom-scrollbar">
                            {tasks.filter(t => t.column === col.id).map(task => (
                                <KanbanCard key={task.id} task={task} onDragStart={handleDragStart} />
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {/* Agent Swimlane */}
            <div className="shrink-0 mt-4 p-4 bg-black/30 border-t border-white/10 rounded-t-lg">
                <h3 className="font-mono text-sm text-gray-400 mb-3">AGENT_SWIMLANE</h3>
                <div className="grid grid-cols-4 gap-4">
                    {AGENTS.map(agent => (
                        <div 
                            key={agent.id}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={() => handleDropOnAgent(agent)}
                            className="p-4 border border-dashed border-white/20 rounded-lg hover:bg-purple/10 hover:border-purple transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <Bot className="text-purple" />
                                <div>
                                    <h4 className="font-bold text-white">{agent.name}</h4>
                                    <p className="text-xs text-gray-400">{agent.specialization}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>

        <AnimatePresence>
            {delegationModal.visible && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center" onClick={() => setDelegationModal({ visible: false })}>
                    <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }} className="w-full max-w-md bg-panel border border-white/20 rounded-xl p-6" onClick={e => e.stopPropagation()}>
                        <h3 className="font-mono text-lg text-white mb-2">Confirm Delegation</h3>
                        <p className="text-gray-400 mb-6">Assign task <span className="text-cyan">"{delegationModal.task?.title}"</span> to <span className="text-purple">{delegationModal.agent?.name}</span>?</p>
                        <div className="flex justify-end gap-4">
                            <NeonButton variant="secondary" onClick={() => setDelegationModal({ visible: false })}>Cancel</NeonButton>
                            <NeonButton variant="primary" onClick={confirmDelegation}>Confirm & Execute</NeonButton>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
      </>
   );
};

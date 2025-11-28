import React, { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Layout } from './components/Layout';
import { GlassCard } from './components/GlassCard';
import { NeonButton } from './components/NeonButton';
import { TerminalText } from './components/TerminalText';
import { ScrambleText } from './components/ScrambleText';
import { KnowledgeNexus } from './components/KnowledgeNexus';
import { IngestStation } from './components/IngestStation';
import { DeepResearch } from './components/DeepResearch';
import { WorkflowConstruct } from './components/WorkflowConstruct';
import { MissionControlBoard } from './components/MissionControlBoard';
import { DependencyTimeline } from './components/DependencyTimeline';
import { StrategyDeck } from './components/StrategyDeck';
import { PmDissection } from './components/PmDissection';
import { DecisionFlowMap } from './components/DecisionFlowMap';
import { SoundProvider } from './components/SoundManager';
import { ContextItem } from './components/ContextPrism';
import { Activity, Shield, Cpu, Terminal, Wifi, Database } from 'lucide-react';
import { useProjects, useCurrentProject } from '@src/hooks/useProjects';
import { useCortexStore } from '@src/state/cortexStore';
import { Node, Edge } from 'reactflow';

// Mock Context Data
const INITIAL_CONTEXT_ITEMS: ContextItem[] = [
  { id: 'c1', name: 'Project_Titan_Specs.pdf', type: 'pdf', tokens: 45000 },
  { id: 'c2', name: 'auth_middleware.rs', type: 'repo', tokens: 12500 },
  { id: 'c3', name: 'user_session.ts', type: 'repo', tokens: 8200 },
  { id: 'c4', name: 'DeepResearch_Chat_Log_001', type: 'chat', tokens: 4100 },
];

// --- Mock Graph Data for WorkflowConstruct ---
const WORKFLOW_NODES: Node[] = [
  { id: 'start', position: { x: 250, y: 0 }, data: { label: '__start__' } },
  { id: 'retrieve', position: { x: 250, y: 100 }, data: { label: 'retrieve_docs' } },
  { id: 'grade', position: { x: 250, y: 200 }, data: { label: 'grade_documents' } },
  { id: 'generate', position: { x: 0, y: 300 }, data: { label: 'generate_answer' } },
  { id: 'web_search', position: { x: 500, y: 300 }, data: { label: 'web_search_tool' } },
  { id: 'finalize', position: { x: 250, y: 450 }, data: { label: '__end__' } },
];

const WORKFLOW_EDGES: Edge[] = [
  { id: 'e1', source: 'start', target: 'retrieve' },
  { id: 'e2', source: 'retrieve', target: 'grade' },
  { id: 'e3', source: 'grade', target: 'generate' },
  { id: 'e4', source: 'grade', target: 'web_search' },
  { id: 'e5', source: 'web_search', target: 'generate' },
  { id: 'e6', source: 'generate', target: 'finalize' },
];

const AppContent: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<'nominal' | 'warning' | 'critical' | 'warming_up'>('nominal');
  const [activeTab, setActiveTab] = useState('mission_control'); 
  const [vram, setVram] = useState(42);
  const [logs, setLogs] = useState<string[]>([
    "INITIALIZING_NEXUS_CORE...",
    "LOADING_MODULES [||||||||||] 100%",
    "ESTABLISHING_SECURE_UPLINK...",
    "CONNECTED_TO_MAIN_FRAME_V2.4"
  ]);

  // Workflow Simulation State
  const [wfActiveNode, setWfActiveNode] = useState<string | null>(null);
  const [wfVisited, setWfVisited] = useState<string[]>([]);

  // Context State
  const [contextItems, setContextItems] = useState<ContextItem[]>(INITIAL_CONTEXT_ITEMS);

  // Load projects and set current project
  const { data: projects, isLoading: projectsLoading, error: projectsError } = useProjects();
  const { project: currentProject } = useCurrentProject();
  const setCurrentProjectId = useCortexStore((s) => s.setCurrentProjectId);

  // Set first project as current if none selected
  useEffect(() => {
    if (projects && projects.length > 0 && !currentProject) {
      setCurrentProjectId(projects[0].id);
    }
  }, [projects, currentProject, setCurrentProjectId]);

  // Show loading state while projects are loading
  if (projectsLoading) {
    return (
      <div className="flex h-screen w-full bg-void text-white items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan mx-auto mb-4"></div>
          <p className="text-gray-400 font-mono">Loading projects...</p>
        </div>
      </div>
    );
  }

  // Show error state if projects failed to load
  if (projectsError) {
    return (
      <div className="flex h-screen w-full bg-void text-white items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-4">Failed to load projects</div>
          <p className="text-gray-400 font-mono text-sm">{projectsError.message}</p>
        </div>
      </div>
    );
  }

  const handleEjectContext = (id: string) => {
    setContextItems(prev => prev.filter(item => item.id !== id));
    setLogs(prev => [...prev, `[CONTEXT_MGR] Ejected item ${id} from memory.`].slice(-8));
  };

  useEffect(() => {
    // Simulate incoming logs and system fluctuations
    const interval = setInterval(() => {
      const newLogs = [
        `DATA_PACKET_RECEIVED: ${Math.random().toString(36).substring(7).toUpperCase()}`,
        `CHECKING_INTEGRITY... OK`,
        `SYNC_RATE: ${(Math.random() * 100).toFixed(2)}ms`,
        `ALLOCATING_TENSORS...`,
        `[GRAPH_ENG] Indexing node ${Math.floor(Math.random() * 9000)}...`,
        `[VRAM_MON] Garbage collection cycle complete.`
      ];
      setLogs(prev => [...prev, newLogs[Math.floor(Math.random() * newLogs.length)]].slice(-8));
      
      setVram(prev => {
        const diff = Math.floor(Math.random() * 10) - 4;
        const newVal = prev + diff;
        return newVal > 95 ? 95 : newVal < 20 ? 20 : newVal;
      });

    }, 2500);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (systemStatus === 'warning') {
      setVram(89);
    } else {
      setVram(42);
    }
  }, [systemStatus]);

  // --- Workflow Simulation Logic ---
  useEffect(() => {
    if (activeTab !== 'workflow') return;

    // A simple linear simulation path for demo purposes
    // Path: start -> retrieve -> grade -> web_search -> generate -> finalize
    const sequence = ['start', 'retrieve', 'grade', 'web_search', 'generate', 'finalize'];
    let step = 0;

    const runStep = () => {
      if (step >= sequence.length) {
        step = 0;
        setWfVisited([]);
        setWfActiveNode(null);
        setTimeout(runStep, 2000); // Pause before restart
        return;
      }

      const currentNode = sequence[step];
      setWfActiveNode(currentNode);
      setWfVisited(prev => [...new Set([...prev, currentNode])]); // Add to visited

      step++;
      setTimeout(runStep, 1500); // Time between steps
    };

    const timer = setTimeout(runStep, 500);
    return () => clearTimeout(timer);
  }, [activeTab]);


  // Calculate used tokens for Layout header based on ContextPrism items
  const usedTokens = contextItems.reduce((acc, i) => acc + i.tokens, 0);

  // Motion variants for glitch/slide effect
  const pageVariants = {
    initial: { 
      opacity: 0, 
      x: -10,
      filter: 'blur(5px)' 
    },
    animate: { 
      opacity: 1, 
      x: 0,
      filter: 'blur(0px)',
      transition: { duration: 0.3, ease: 'circOut' }
    },
    exit: { 
      opacity: 0, 
      x: 10,
      filter: 'blur(5px)',
      transition: { duration: 0.2 }
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'mission_control':
        return (
          <motion.div 
             key="mission_control"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
            <MissionControlBoard />
          </motion.div>
        );

      case 'timeline':
        return (
          <motion.div 
             key="timeline"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
            <DependencyTimeline />
          </motion.div>
        );

      case 'roadmap':
        return (
          <motion.div 
             key="roadmap"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
            <DecisionFlowMap />
          </motion.div>
        );
        
      import { ReactFlowProvider } from 'reactflow';
// ... other imports

// ... inside AppContent component, in the renderContent function

      case 'strategy':
        return (
          <motion.div 
             key="strategy"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
            <ReactFlowProvider>
              <StrategyDeck />
            </ReactFlowProvider>
          </motion.div>
        );

      case 'pm_dissection':
        return (
          <motion.div 
             key="pm_dissection"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
            <PmDissection />
          </motion.div>
        );

      case 'nexus':
        return (
          <motion.div 
            key="nexus"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="h-[calc(100vh-140px)] w-full flex flex-col gap-4"
          >
             <div className="flex justify-between items-end">
               <div>
                  <h2 className="text-2xl font-mono text-white tracking-wide"><ScrambleText text="KNOWLEDGE_NEXUS" /></h2>
                  <p className="text-gray-500 font-mono text-xs mt-1">SEMANTIC GRAPH VISUALIZER // V3.1</p>
               </div>
               <div className="flex gap-2">
                  <span className="flex items-center gap-1 text-xs font-mono text-cyan"><div className="w-2 h-2 rounded-full bg-cyan"></div> PDF</span>
                  <span className="flex items-center gap-1 text-xs font-mono text-amber"><div className="w-2 h-2 bg-amber"></div> REPO</span>
                  <span className="flex items-center gap-1 text-xs font-mono text-purple"><div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-b-[8px] border-b-purple"></div> CHAT</span>
               </div>
             </div>
             <div className="flex items-center justify-center h-full bg-panel/50 rounded-xl">
               <p className="text-gray-400 font-mono">Knowledge Nexus - Coming Soon</p>
             </div>
          </motion.div>
        );

      case 'ingest':
        return (
           <motion.div 
             key="ingest"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
             <IngestStation />
           </motion.div>
        );

      case 'research':
        return (
          <motion.div 
             key="research"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
           >
            <DeepResearch />
          </motion.div>
        );

      case 'workflow':
        return (
          <motion.div 
             key="workflow"
             variants={pageVariants}
             initial="initial"
             animate="animate"
             exit="exit"
             className="h-[calc(100vh-140px)] w-full flex flex-col gap-4"
           >
            <div>
               <h2 className="text-2xl font-mono text-white tracking-wide">LANGGRAPH_CONSTRUCT</h2>
               <p className="text-gray-500 font-mono text-xs mt-1">REAL-TIME EXECUTION TRACING</p>
            </div>
            <WorkflowConstruct 
              graphState={{
                nodes: WORKFLOW_NODES,
                edges: WORKFLOW_EDGES,
                activeNodeId: wfActiveNode,
                visitedNodeIds: wfVisited
              }}
            />
          </motion.div>
        );

      default:
        // Dashboard
        return (
          <motion.div 
            key="dashboard"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="space-y-8 pb-10"
          >
            {/* Actions Bar */}
            <div className="flex flex-col md:flex-row justify-between items-end gap-4 pb-2">
               <div>
                 <h2 className="text-2xl font-mono text-white tracking-wide">DASHBOARD_<span className="text-gray-600">OVERVIEW</span></h2>
                 <p className="text-gray-500 font-mono text-xs mt-1">REAL-TIME MONITORING NODE #8821</p>
               </div>
               <div className="flex gap-4">
                 <NeonButton variant="cyan" onClick={() => setSystemStatus('nominal')}>
                   SYS_NOMINAL
                 </NeonButton>
                 <NeonButton variant="amber" onClick={() => setSystemStatus('warning')}>
                   SIM_WARNING
                 </NeonButton>
                 <NeonButton variant="purple" onClick={() => setActiveTab('nexus')}>
                   VIEW_GRAPH
                 </NeonButton>
               </div>
            </div>

            {/* Main Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
              
              {/* Sidebar / Stats */}
              <div className="md:col-span-3 space-y-6">
                <GlassCard variant="cyan" title="CORE_METRICS">
                  <div className="space-y-4 font-mono text-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-400">CPU_LOAD</span>
                      <span className="text-cyan"><ScrambleText text="34%" duration={800} /></span>
                    </div>
                    <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                      <div className="h-full bg-cyan w-[34%] shadow-neon-cyan"></div>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-gray-400">VRAM_USAGE</span>
                      <span className={systemStatus === 'warning' ? 'text-amber animate-pulse' : 'text-cyan'}>
                        <ScrambleText text={`${vram}%`} duration={500} />
                      </span>
                    </div>
                    <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${systemStatus === 'warning' ? 'bg-amber shadow-neon-amber' : 'bg-cyan shadow-neon-cyan'}`}
                        style={{ width: `${vram}%` }}
                      ></div>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-gray-400">NET_UPLINK</span>
                      <span className="text-purple"><ScrambleText text="1.2 GB/s" duration={1200} /></span>
                    </div>
                    <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                      <div className="h-full bg-purple w-[78%] shadow-neon-purple"></div>
                    </div>
                  </div>
                </GlassCard>

                <GlassCard variant="void" title="ACTIVE_NODES">
                  <div className="grid grid-cols-2 gap-2">
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="bg-white/5 p-2 rounded border border-white/10 flex items-center justify-center flex-col gap-1 hover:bg-white/10 transition-colors cursor-pointer group">
                        <Database size={16} className="text-gray-500 group-hover:text-cyan transition-colors" />
                        <span className="text-xs text-gray-400 font-mono">NODE_0{i}</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              </div>

              {/* Center / Main Display */}
              <div className="md:col-span-6 space-y-6">
                <GlassCard variant="primary" className="h-[400px] flex flex-col relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-full pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
                  
                  <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-2">
                    <Terminal size={18} className="text-cyan" />
                    <h2 className="font-mono text-cyan tracking-wider text-sm">MAIN_TERMINAL_OUTPUT</h2>
                  </div>

                  <div className="flex-1 overflow-y-auto font-mono text-sm space-y-2 p-2 relative z-10 scrollbar-hide">
                     {logs.map((log, index) => (
                       <div key={index} className="flex gap-2 hover:bg-white/5 p-1 rounded transition-colors">
                         <span className="text-gray-600 select-none">{`>`}</span>
                         <span className={`${log.includes('WARNING') ? 'text-amber' : 'text-gray-300'}`}>
                           <TerminalText text={log} speed={5} />
                         </span>
                       </div>
                     ))}
                     <div className="animate-pulse text-cyan">_</div>
                  </div>
                </GlassCard>
                
                <div className="grid grid-cols-2 gap-6">
                  <GlassCard variant="purple" title="AI_REASONING">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-purple/10 rounded-full border border-purple/30 shadow-neon-purple">
                        <Cpu className="text-purple" />
                      </div>
                      <div>
                        <div className="text-xs text-gray-400 uppercase tracking-wider">Current Task</div>
                        <div className="text-white font-mono text-sm"><ScrambleText text="Optimizing neural pathways..." duration={2000} /></div>
                      </div>
                    </div>
                  </GlassCard>

                  <GlassCard variant="amber" title="SECURITY">
                    <div className="flex items-center gap-4">
                      <div className={`p-3 bg-amber/10 rounded-full border border-amber/30 ${systemStatus === 'warning' ? 'animate-pulse shadow-neon-amber' : ''}`}>
                        <Shield className="text-amber" />
                      </div>
                      <div>
                        <div className="text-xs text-gray-400 uppercase tracking-wider">Firewall</div>
                        <div className="text-white font-mono text-sm">
                          {systemStatus === 'warning' ? 'INTRUSION DETECTED' : 'ACTIVE'}
                        </div>
                      </div>
                    </div>
                  </GlassCard>
                </div>
              </div>

              {/* Right Column / Actions */}
              <div className="md:col-span-3 space-y-6">
                <GlassCard title="QUICK_ACTIONS" variant="void">
                   <div className="flex flex-col gap-3">
                     <NeonButton variant="cyan" fullWidth icon={<Wifi size={16}/>}>SCAN_NETWORK</NeonButton>
                     <NeonButton variant="purple" fullWidth icon={<Activity size={16}/>}>DIAGNOSTICS</NeonButton>
                     <NeonButton variant="amber" fullWidth icon={<Shield size={16}/>}>FLUSH_CACHE</NeonButton>
                   </div>
                </GlassCard>

                <div className="p-4 rounded-xl border border-white/10 bg-panel relative overflow-hidden group hover:border-cyan/30 transition-colors">
                   <div className="absolute inset-0 bg-gradient-to-br from-cyan/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                   <h3 className="font-mono text-xs text-gray-400 mb-2">SYSTEM_RESOURCE</h3>
                   <div className="flex items-end gap-1 h-24 mt-4">
                     {[40, 60, 30, 80, 50, 90, 70, 40, 60].map((h, i) => (
                       <motion.div 
                        key={i} 
                        initial={{ height: '0%' }}
                        animate={{ height: `${h}%` }}
                        transition={{ duration: 1, delay: i * 0.1 }}
                        className="flex-1 bg-cyan/20 hover:bg-cyan/80 transition-colors duration-300 rounded-sm cursor-help"
                       ></motion.div>
                     ))}
                   </div>
                </div>
              </div>

            </div>
          </motion.div>
        );
    }
  };

  return (
    <Layout
      currentModel="Llama-3.3-70B"
      vramUsage={vram}
      contextUsage={{ used: Math.floor(usedTokens / 1000), total: 128, unit: 'k' }}
      systemStatus={systemStatus}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      logs={logs}
      contextItems={contextItems}
      onEjectContext={handleEjectContext}
    >
      <AnimatePresence mode='wait'>
         {renderContent()}
      </AnimatePresence>
    </Layout>
  );
}

const App: React.FC = () => {
  return (
    <SoundProvider>
      <AppContent />
    </SoundProvider>
  );
}

export default App;

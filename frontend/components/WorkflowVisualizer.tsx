import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  Node, 
  Edge, 
  Handle, 
  Position, 
  useNodesState, 
  useEdgesState,
  MarkerType
} from 'reactflow';
import { Play, Pause, RefreshCw, Box, Layers, AlertCircle, GitMerge, BrainCircuit, Terminal, CheckCircle, X, Activity, Repeat } from 'lucide-react';
import { NeonButton } from './NeonButton';
import { GlassCard } from './GlassCard';

// --- Custom Node Component ---
const NeonNode = ({ data, selected }: { data: any, selected: boolean }) => {
  const { label, type, status, icon: Icon, iteration } = data;
  
  // Dynamic styling based on type and status
  const getStyles = () => {
    switch (type) {
      case 'start': return 'border-cyan text-cyan shadow-neon-cyan';
      case 'end': return 'border-green-500 text-green-500 shadow-neon-green';
      case 'decision': return 'border-amber text-amber shadow-neon-amber rounded-full';
      case 'process': 
      default: return 'border-purple text-purple shadow-neon-purple';
    }
  };

  const getStatusColor = () => {
    if (status === 'active') return 'bg-white text-black animate-pulse';
    if (status === 'completed') return type === 'decision' ? 'bg-amber/20 text-amber' : 'bg-cyan/20 text-cyan';
    return 'bg-white/5 text-gray-500';
  };

  const baseColor = getStyles();
  const isDecision = type === 'decision';

  return (
    <div className={`
      relative min-w-[160px] p-3 border-2 bg-black/80 backdrop-blur-md transition-all duration-300
      ${selected ? `${baseColor} scale-105` : 'border-white/20 text-gray-400 hover:border-white/40'}
      ${isDecision ? 'rounded-2xl px-6' : 'rounded-lg'}
    `}>
      {/* Target Handle (Input) */}
      {type !== 'start' && (
        <Handle type="target" position={Position.Top} className="!bg-white !w-3 !h-1 !rounded-none" />
      )}

      {/* Decision Node uses Right/Left handles for loops sometimes, but we stick to bottom for simplicity or usage of multiple handles */}
      {type === 'decision' && (
         <Handle type="source" id="retry" position={Position.Left} className="!bg-amber !w-2 !h-2 !rounded-full !-left-1.5" />
      )}

      <div className="flex items-center gap-3 justify-center">
         <div className={`p-2 rounded-full ${getStatusColor()}`}>
            {Icon ? <Icon size={16} /> : <Box size={16} />}
         </div>
         <div className={isDecision ? 'text-center' : ''}>
            <div className="text-[10px] font-mono uppercase tracking-wider opacity-70">{type}</div>
            <div className="font-bold text-sm font-mono whitespace-nowrap">{label}</div>
         </div>
         {iteration > 0 && (
             <div className="absolute -top-2 -right-2 w-5 h-5 bg-amber text-black rounded-full flex items-center justify-center text-xs font-bold border border-white">
                 {iteration}
             </div>
         )}
      </div>
      
      {/* Active Indicator Line */}
      {status === 'active' && !isDecision && (
        <div className={`absolute bottom-0 left-0 h-[2px] w-full animate-loading-bar ${type === 'error' ? 'bg-amber' : type === 'start' ? 'bg-cyan' : 'bg-purple'}`}></div>
      )}

      {/* Source Handle (Output) */}
      {type !== 'end' && (
         <Handle type="source" position={Position.Bottom} className="!bg-white !w-3 !h-1 !rounded-none" />
      )}
    </div>
  );
};

const nodeTypes = {
  neon: NeonNode,
};

// Mock data removed - should fetch from agent runs API
// TODO: Replace with real agent run workflow state from useAgentRuns hook

export const WorkflowVisualizer: React.FC = () => {
  const { project } = useCurrentProject();
  const projectId = project?.id;
  // TODO: Use useAgentRuns hook to fetch real workflow state
  // const { data: agentRuns } = useAgentRuns(projectId);
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Simulation Sequence (Flattened loop for demo)
  // Logic: Start -> Planner -> Draft -> Critique -> Router (Fail) -> Draft -> Critique -> Router (Pass) -> Final
  const simulationSequence = [
    { active: 'start', payloadUpdate: {} },
    { active: 'planner', payloadUpdate: { status: 'planning_complete' } },
    { active: 'draft', payloadUpdate: { iteration: 1, code_len: 120 } },
    { active: 'critique', payloadUpdate: { score: 0.6, comments: "Syntax error in loop" } },
    { active: 'router', edge: 'e6', payloadUpdate: { decision: "RETRY" } }, // Triggers loop
    { active: 'draft', payloadUpdate: { iteration: 2, code_len: 145, fix: "Corrected syntax" } },
    { active: 'critique', payloadUpdate: { score: 0.95, comments: "Looks good" } },
    { active: 'router', edge: 'e5', payloadUpdate: { decision: "APPROVE" } }, // Triggers success
    { active: 'final', payloadUpdate: { done: true } }
  ];

  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentStepIndex(prev => {
        if (prev >= simulationSequence.length) {
          setIsPlaying(false);
          return 0; // Reset or Stay? Let's stop.
        }
        
        const step = simulationSequence[prev];
        
        // 1. Update Nodes Status
        setNodes((nds) => nds.map((node) => {
          // If this is the active node
          if (node.id === step.active) {
             // If it's the draft node, increment iteration visually if visiting again
             const newIter = node.id === 'draft' ? (node.data.iteration || 0) + 1 : node.data.iteration;
             return { 
                 ...node, 
                 data: { 
                     ...node.data, 
                     status: 'active', 
                     iteration: newIter,
                     payload: { ...node.data.payload, ...step.payloadUpdate }
                 } 
             };
          }
          // If we passed it previously, mark completed (unless we are looping back, then maybe keep it?) 
          // For simple viz, let's keep everything 'visited' as completed, 'current' as active.
          // But since we revisit 'draft', we need to handle that.
          
          // Simple logic: If index of this node in sequence < current step, it's completed? 
          // Not quite because of loops. 
          // Let's just say: If it's NOT active, and was visited before, it is completed.
          if (node.data.status === 'active') {
             return { ...node, data: { ...node.data, status: 'completed' } };
          }
          return node;
        }));

        // 2. Animate Edges
        setEdges((eds) => eds.map((edge) => {
           // Reset all animations first? No, keep history trail maybe?
           // Let's only animate the edge relevant to this step.
           // If step.edge is defined, that's the active edge.
           // Or imply edge based on previous node -> current node.
           
           if (step.edge && edge.id === step.edge) {
               return { ...edge, animated: true, style: { stroke: '#ffbf00', strokeWidth: 2 } }; // Amber for decision paths
           }
           
           // Standard path logic
           if (prev > 0) {
               const prevNodeId = simulationSequence[prev - 1].active;
               if (edge.source === prevNodeId && edge.target === step.active) {
                   return { ...edge, animated: true, style: { stroke: '#00f0ff', strokeWidth: 2 } };
               }
           }
           
           // If passed, keep colored but stop animation? or keep animation.
           // Simplify: Just highlight active path.
           return { ...edge, animated: false, style: { stroke: '#333', strokeWidth: 1 } };
        }));

        return prev + 1;
      });
    }, 1200);

    return () => clearInterval(interval);
  }, [isPlaying, setNodes, setEdges]);

  // Handle Reset
  const handleReset = () => {
      setIsPlaying(false);
      setCurrentStepIndex(0);
      setNodes(initialNodes);
      setEdges(initialEdges);
  };

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="h-[calc(100vh-140px)] w-full relative flex animate-fade-in">
      
      {/* Workflow Canvas */}
      <div className="flex-1 h-full rounded-xl overflow-hidden border border-white/10 bg-void relative">
         <div className="absolute top-4 left-4 z-10 flex gap-2">
            <NeonButton variant="cyan" onClick={() => setIsPlaying(!isPlaying)} icon={isPlaying ? <Pause size={14}/> : <Play size={14}/>}>
               {isPlaying ? 'PAUSE_ORCHESTRATION' : 'RUN_SIMULATION'}
            </NeonButton>
            <NeonButton variant="purple" onClick={handleReset} icon={<RefreshCw size={14}/>}>
               RESET
            </NeonButton>
         </div>

         {/* Legend */}
         <div className="absolute top-4 right-4 z-10 bg-black/60 backdrop-blur p-2 rounded border border-white/10 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-[10px] font-mono text-gray-400">
                <div className="w-2 h-2 rounded-full bg-cyan shadow-[0_0_5px_cyan]"></div> Active Path
            </div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-gray-400">
                <div className="w-2 h-2 rounded-full bg-amber shadow-[0_0_5px_orange]"></div> Decision/Loop
            </div>
         </div>

         <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
            minZoom={0.5}
            defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
         >
            <Background color="#222" gap={25} size={1} />
            <Controls className="bg-panel border border-white/10 text-white fill-white" />
         </ReactFlow>
      </div>

      {/* State Inspector Sidebar */}
      <div className={`
         absolute top-4 right-4 bottom-4 w-80 bg-panel/90 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl
         transform transition-transform duration-300 ease-out flex flex-col z-20
         ${selectedNode ? 'translate-x-0' : 'translate-x-[110%]'}
      `}>
         {selectedNode && (
            <>
               <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/40 rounded-t-xl">
                  <div className="flex items-center gap-2">
                     <Layers size={16} className="text-cyan" />
                     <span className="font-mono font-bold text-sm text-white uppercase">NODE_INSPECTOR</span>
                  </div>
                  <button onClick={() => setSelectedNode(null)} className="text-gray-500 hover:text-white">
                     <X size={18} />
                  </button>
               </div>
               
               <div className="p-4 space-y-6 flex-1 overflow-y-auto">
                  {/* Header Metrics */}
                  <div className="grid grid-cols-2 gap-3">
                      <div className="bg-white/5 p-2 rounded border border-white/10">
                          <label className="text-[9px] uppercase tracking-widest text-gray-500 font-mono block">Latency</label>
                          <div className="text-cyan font-mono text-lg">45ms</div>
                      </div>
                      <div className="bg-white/5 p-2 rounded border border-white/10">
                          <label className="text-[9px] uppercase tracking-widest text-gray-500 font-mono block">Status</label>
                          <div className={`text-xs font-mono font-bold mt-1 ${
                              selectedNode.data.status === 'active' ? 'text-green-400 animate-pulse' : 'text-gray-400'
                          }`}>
                              {selectedNode.data.status.toUpperCase()}
                          </div>
                      </div>
                  </div>

                  {/* JSON State View */}
                  <div className="flex-1">
                     <div className="flex items-center justify-between mb-2">
                        <label className="text-[10px] uppercase tracking-widest text-gray-500 font-mono">Current State</label>
                        <span className="text-[9px] text-gray-600 font-mono">Read-Only</span>
                     </div>
                     <div className="relative group">
                        <div className="absolute -inset-1 bg-gradient-to-r from-cyan/20 to-purple/20 rounded-lg blur opacity-10 group-hover:opacity-30 transition duration-1000"></div>
                        <pre className="relative p-3 bg-black/90 rounded border border-white/10 text-[10px] font-mono text-green-400 overflow-x-auto custom-scrollbar shadow-inner h-48">
                           {JSON.stringify(selectedNode.data.payload, null, 2)}
                        </pre>
                     </div>
                  </div>

                  {/* Activity Log (Mock) */}
                  <div>
                      <label className="text-[10px] uppercase tracking-widest text-gray-500 font-mono block mb-2">Execution Log</label>
                      <div className="space-y-2">
                          <div className="flex gap-2 items-start text-[10px] font-mono text-gray-400">
                             <span className="text-gray-600">[14:02:01]</span>
                             <span>Initialized node context</span>
                          </div>
                          <div className="flex gap-2 items-start text-[10px] font-mono text-gray-400">
                             <span className="text-gray-600">[14:02:02]</span>
                             <span>Loaded prompt template: "coder_v2"</span>
                          </div>
                          {selectedNode.data.iteration > 0 && (
                             <div className="flex gap-2 items-start text-[10px] font-mono text-amber">
                                <span className="text-amber/60">[14:02:05]</span>
                                <span>Re-entry detected (Loop #{selectedNode.data.iteration})</span>
                             </div>
                          )}
                      </div>
                  </div>
               </div>
               
               <div className="p-4 border-t border-white/10 bg-black/20 text-center">
                  <span className="text-[9px] text-gray-600 font-mono">ID: {selectedNode.id} // TYPE: {selectedNode.type}</span>
               </div>
            </>
         )}
      </div>
    </div>
  );
};

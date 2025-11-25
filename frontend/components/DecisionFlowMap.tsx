
import React, { useCallback, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Handle,
  Position,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import { GitFork, CheckSquare, Database, Server, Code, Shield, HelpCircle } from 'lucide-react';
import { OptionInspector, DecisionData } from './OptionInspector';

// --- Custom Task Node ---
const TaskNode = ({ data }: { data: any }) => {
  return (
    <div className="relative min-w-[150px] bg-black/80 backdrop-blur-md border border-cyan/50 rounded-lg p-3 shadow-[0_0_15px_rgba(0,240,255,0.2)] hover:border-cyan hover:shadow-neon-cyan transition-all duration-300">
      <Handle type="target" position={Position.Top} className="!bg-white !w-2 !h-2 !rounded-sm" />
      
      <div className="flex items-center gap-3">
        <div className="p-1.5 rounded bg-cyan/10 border border-cyan/30 text-cyan">
          {data.icon || <CheckSquare size={14} />}
        </div>
        <div>
          <div className="text-[9px] text-cyan/70 font-mono uppercase tracking-wider">Task</div>
          <div className="text-xs font-bold text-white font-mono">{data.label}</div>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-white !w-2 !h-2 !rounded-sm" />
    </div>
  );
};

// --- Custom Decision Node ---
const DecisionNode = ({ data }: { data: any }) => {
  return (
    <div className="relative w-32 h-32 flex items-center justify-center">
      <Handle type="target" position={Position.Top} className="!bg-amber !w-2 !h-2 !rounded-full -mt-2 z-50" />
      
      {/* Rotated Diamond Shape */}
      <div className={`
        absolute inset-0 bg-black/80 backdrop-blur-md border-2 
        ${data.isSelected ? 'border-amber bg-amber/10 shadow-neon-amber' : 'border-amber/60 shadow-[0_0_15px_rgba(255,191,0,0.2)]'}
        rotate-45 rounded-lg transition-all duration-300 group-hover:border-amber
      `}></div>

      {/* Content (Un-rotated) */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center p-2">
         <HelpCircle size={20} className={`mb-1 ${data.isSelected ? 'text-white' : 'text-amber'}`} />
         <span className="text-[10px] font-mono font-bold text-amber/80 uppercase tracking-widest">Decision</span>
         <span className="text-xs font-bold text-white font-mono leading-tight">{data.label}</span>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-amber !w-2 !h-2 !rounded-full -mb-2 z-50" />
    </div>
  );
};

const nodeTypes = {
  task: TaskNode,
  decision: DecisionNode,
};

// --- Initial Data ---
const initialNodes: Node[] = [
  { 
    id: '1', type: 'task', position: { x: 400, y: 0 }, 
    data: { label: 'Project Init', icon: <Code size={14} /> } 
  },
  { 
    id: '2', type: 'decision', position: { x: 365, y: 120 }, 
    data: { label: 'Stack Choice?' } 
  },
  { 
    id: '3a', type: 'task', position: { x: 150, y: 300 }, 
    data: { label: 'Setup Axum', icon: <GitFork size={14} /> } 
  },
  { 
    id: '3b', type: 'task', position: { x: 650, y: 300 }, 
    data: { label: 'Setup FastAPI', icon: <Database size={14} /> } 
  },
  { 
    id: '4', type: 'task', position: { x: 400, y: 450 }, 
    data: { label: 'Websocket API', icon: <Server size={14} /> } 
  },
  { 
    id: '5', type: 'task', position: { x: 400, y: 550 }, 
    data: { label: 'Security Audit', icon: <Shield size={14} /> } 
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', type: 'smoothstep', style: { stroke: '#555' } },
  
  // Branch A
  { 
    id: 'e2-3a', source: '2', target: '3a', type: 'smoothstep', 
    label: 'Option A: Rust', 
    style: { stroke: '#bd00ff', strokeWidth: 1.5 },
    labelStyle: { fill: '#bd00ff', fontWeight: 700, fontFamily: 'JetBrains Mono', fontSize: 10 },
    labelBgStyle: { fill: '#1a0526', fillOpacity: 0.8 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#bd00ff' } 
  },
  
  // Branch B
  { 
    id: 'e2-3b', source: '2', target: '3b', type: 'smoothstep', 
    label: 'Option B: Python', 
    style: { stroke: '#bd00ff', strokeWidth: 1.5 },
    labelStyle: { fill: '#bd00ff', fontWeight: 700, fontFamily: 'JetBrains Mono', fontSize: 10 },
    labelBgStyle: { fill: '#1a0526', fillOpacity: 0.8 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#bd00ff' } 
  },

  // Re-merge
  { id: 'e3a-4', source: '3a', target: '4', type: 'smoothstep', style: { stroke: '#555' } },
  { id: 'e3b-4', source: '3b', target: '4', type: 'smoothstep', style: { stroke: '#555' } },
  { id: 'e4-5', source: '4', target: '5', type: 'smoothstep', style: { stroke: '#555' } },
];

// --- Mock Data Generator ---
const getDecisionData = (nodeId: string): DecisionData => {
  return {
    id: nodeId,
    question: "Which framework to use for the Real-time Websocket? (Axum vs FastAPI)",
    options: [
      {
        id: "opt-1",
        label: "Option A: Axum (Rust)",
        summary: "Pros: Zero-cost abstraction, extremely high concurrency handling, type safety. Cons: Steep learning curve, slower compile times.",
        pros: ["Performance", "Safety"],
        cons: ["Complexity"],
        analysis_complete: true,
        context_links: [
          { type: "code", title: "auth_middleware.rs" },
          { type: "pdf", title: "Protocol_RFC_V4.pdf" }
        ]
      },
      {
        id: "opt-2",
        label: "Option B: FastAPI (Python)",
        summary: "Pros: Rapid development velocity, huge ecosystem, fits existing ML stack. Cons: GIL limitations, higher memory footprint per connection.",
        pros: ["Speed of Dev", "Ecosystem"],
        cons: ["Performance"],
        analysis_complete: true,
        context_links: [
          { type: "code", title: "api_routes.py" },
          { type: "chat", title: "Arch_Discussion_Log_04.txt" }
        ]
      }
    ]
  };
};

export const DecisionFlowMap: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [lastEvent, setLastEvent] = useState<string>('WAITING_FOR_INPUT');
  
  // Inspector State
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [activeDecision, setActiveDecision] = useState<DecisionData | null>(null);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === 'decision') {
      setLastEvent(`DECISION_NODE_SELECTED: ${node.data.label}`);
      
      // Update Visuals
      setNodes((nds) => nds.map((n) => {
        if (n.id === node.id) {
          return { ...n, data: { ...n.data, isSelected: !n.data.isSelected } };
        }
        return { ...n, data: { ...n.data, isSelected: false } };
      }));

      // Generate Data & Open Inspector
      const mockData = getDecisionData(node.id);
      setActiveDecision(mockData);
      setInspectorOpen(true);

    } else {
      setLastEvent(`TASK_INSPECT: ${node.data.label}`);
      setInspectorOpen(false); // Close if clicking non-decision
    }
  }, [setNodes]);

  const handleContextSelect = (fileName: string) => {
    setLastEvent(`NAVIGATING_TO_CONTEXT: ${fileName}`);
    // In a real app, this would trigger navigation in App.tsx
  };

  return (
    <div className="h-[calc(100vh-140px)] w-full flex flex-col gap-4 animate-fade-in relative">
      <div className="flex justify-between items-end">
         <div>
            <h2 className="text-2xl font-mono text-white tracking-wide">PROJECT_ROADMAP</h2>
            <p className="text-gray-500 font-mono text-xs mt-1">DECISION TREE VISUALIZER</p>
         </div>
         <div className="bg-black/50 border border-white/10 px-3 py-1 rounded text-[10px] font-mono text-amber">
            EVENT_LOG: {lastEvent}
         </div>
      </div>

      <div className="flex-1 border border-white/10 rounded-xl overflow-hidden bg-void relative shadow-2xl">
         <div className="absolute inset-0 pointer-events-none z-0 opacity-20"
             style={{
               backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.1) 1px, transparent 0)',
               backgroundSize: '20px 20px'
             }}>
         </div>

         <ReactFlow
           nodes={nodes}
           edges={edges}
           onNodesChange={onNodesChange}
           onEdgesChange={onEdgesChange}
           onNodeClick={onNodeClick}
           nodeTypes={nodeTypes}
           fitView
           minZoom={0.5}
           proOptions={{ hideAttribution: true }}
         >
           <Background color="#111" gap={20} size={1} />
           <Controls className="bg-panel border border-white/10 text-white fill-white" />
         </ReactFlow>

         {/* Legend Overlay */}
         <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur border border-white/10 p-3 rounded-lg z-10">
            <div className="text-[10px] font-mono text-gray-500 uppercase mb-2">Map Legend</div>
            <div className="flex flex-col gap-2">
               <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded bg-cyan/20 border border-cyan/50"></div>
                  <span className="text-[10px] font-mono text-gray-300">Standard Task</span>
               </div>
               <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rotate-45 bg-amber/20 border border-amber/50 ml-0.5"></div>
                  <span className="text-[10px] font-mono text-gray-300 ml-1">Decision Point</span>
               </div>
               <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-purple"></div>
                  <span className="text-[10px] font-mono text-purple">Variable Path</span>
               </div>
            </div>
         </div>
         
         {/* Inspector Drawer */}
         <OptionInspector 
            isOpen={inspectorOpen} 
            data={activeDecision} 
            onClose={() => setInspectorOpen(false)} 
            onContextSelect={handleContextSelect}
         />
      </div>
    </div>
  );
};


import React, { useCallback, useState, useEffect, useRef } from 'react';
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
  addEdge,
  useReactFlow,
} from 'reactflow';
import { AnimatePresence, motion } from 'framer-motion';
import { GitFork, CheckSquare, Database, Server, Code, Shield, HelpCircle, Plus, BrainCircuit, X } from 'lucide-react';
import { OptionInspector, DecisionData } from './OptionInspector';

// --- MOCK API & HOOK ---
// This would be in a separate file e.g., /hooks/useRoadmapGraph.ts
const MOCK_ROADMAP_DATA = {
  nodes: [
    { id: '1', project_id: 'proj-1', label: 'Project Init', node_type: 'task', metadata: { icon: 'Code' } },
    { id: '2', project_id: 'proj-1', label: 'Stack Choice?', node_type: 'decision', metadata: { 
        question: "Which framework for the Real-time Websocket?",
        options: [
          { id: "opt-1", label: "Option A: Axum (Rust)", summary: "Pros: Zero-cost abstraction, high concurrency. Cons: Steep learning curve.", pros: ["Performance", "Safety"], cons: ["Complexity"], context_links: [{ type: "code", title: "auth_middleware.rs" }] },
          { id: "opt-2", label: "Option B: FastAPI (Python)", summary: "Pros: Rapid development, huge ecosystem. Cons: GIL limitations, higher memory footprint.", pros: ["Speed of Dev", "Ecosystem"], cons: ["Performance"], context_links: [{ type: "code", title: "api_routes.py" }] }
        ]
      } 
    },
    { id: '3a', project_id: 'proj-1', label: 'Setup Axum', node_type: 'task', metadata: { icon: 'GitFork' } },
    { id: '3b', project_id: 'proj-1', label: 'Setup FastAPI', node_type: 'task', metadata: { icon: 'Database' } },
    { id: '4', project_id: 'proj-1', label: 'Websocket API', node_type: 'task', metadata: { icon: 'Server' } },
    { id: '5', project_id: 'proj-1', label: 'Security Audit', node_type: 'task', metadata: { icon: 'Shield' } },
  ],
  edges: [
    { id: 'e1-2', from_node_id: '1', to_node_id: '2' },
    { id: 'e2-3a', from_node_id: '2', to_node_id: '3a', label: 'Option A: Rust' },
    { id: 'e2-3b', from_node_id: '2', to_node_id: '3b', label: 'Option B: Python' },
    { id: 'e3a-4', from_node_id: '3a', to_node_id: '4' },
    { id: 'e3b-4', from_node_id: '3b', to_node_id: '4' },
    { id: 'e4-5', from_node_id: '4', to_node_id: '5' },
  ]
};

const ICONS: { [key: string]: React.ReactNode } = {
  Code: <Code size={14} />,
  GitFork: <GitFork size={14} />,
  Database: <Database size={14} />,
  Server: <Server size={14} />,
  Shield: <Shield size={14} />,
  Default: <CheckSquare size={14} />,
};

const useRoadmapGraph = (projectId: string) => {
  const [data, setData] = useState<any>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API fetch
    setLoading(true);
    setTimeout(() => {
      const formattedNodes = MOCK_ROADMAP_DATA.nodes.map((n, i) => ({
        id: n.id,
        type: n.node_type,
        position: { x: (i % 3) * 250, y: Math.floor(i / 3) * 150 },
        data: {
          label: n.label,
          icon: ICONS[n.metadata?.icon as string] || ICONS.Default,
          ...n.metadata
        }
      }));

      const formattedEdges = MOCK_ROADMAP_DATA.edges.map(e => ({
        id: e.id,
        source: e.from_node_id,
        target: e.to_node_id,
        label: e.label,
        type: 'smoothstep',
        style: { stroke: '#555' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#555' }
      }));
      
      setData({ nodes: formattedNodes, edges: formattedEdges });
      setLoading(false);
    }, 1000);
  }, [projectId]);

  return { data, loading };
};
// --- END MOCK ---


// --- Custom Nodes ---
const TaskNode = ({ data }: { data: any }) => (
  <div className="relative min-w-[150px] bg-black/80 backdrop-blur-md border border-cyan/50 rounded-lg p-3 shadow-[0_0_15px_rgba(0,240,255,0.2)] hover:border-cyan hover:shadow-neon-cyan transition-all duration-300">
    <Handle type="target" position={Position.Top} className="!bg-white !w-2 !h-2 !rounded-sm" />
    <div className="flex items-center gap-3">
      <div className="p-1.5 rounded bg-cyan/10 border border-cyan/30 text-cyan">{data.icon}</div>
      <div>
        <div className="text-[9px] text-cyan/70 font-mono uppercase tracking-wider">Task</div>
        <div className="text-xs font-bold text-white font-mono">{data.label}</div>
      </div>
    </div>
    <Handle type="source" position={Position.Bottom} className="!bg-white !w-2 !h-2 !rounded-sm" />
  </div>
);

const DecisionNode = ({ data, selected }: { data: any, selected: boolean }) => (
  <div className="relative w-32 h-32 flex items-center justify-center group">
    <Handle type="target" position={Position.Top} className="!bg-amber !w-2 !h-2 !rounded-full -mt-2 z-50" />
    <div className={`absolute inset-0 bg-black/80 backdrop-blur-md border-2 ${selected ? 'border-amber bg-amber/10 shadow-neon-amber' : 'border-amber/60 shadow-[0_0_15px_rgba(255,191,0,0.2)]'} rotate-45 rounded-lg transition-all duration-300 group-hover:border-amber`}></div>
    <div className="relative z-10 flex flex-col items-center justify-center text-center p-2">
       <HelpCircle size={20} className={`mb-1 ${selected ? 'text-white' : 'text-amber'}`} />
       <span className="text-[10px] font-mono font-bold text-amber/80 uppercase tracking-widest">Decision</span>
       <span className="text-xs font-bold text-white font-mono leading-tight">{data.label}</span>
    </div>
    <Handle type="source" position={Position.Bottom} className="!bg-amber !w-2 !h-2 !rounded-full -mb-2 z-50" />
  </div>
);

const nodeTypes = { task: TaskNode, decision: DecisionNode };


// --- Main Component ---
export const DecisionFlowMap: React.FC = () => {
  const { data: graphData, loading } = useRoadmapGraph('proj-1');
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [lastEvent, setLastEvent] = useState<string>('GRAPH_INITIALIZING...');
  
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [activeDecision, setActiveDecision] = useState<DecisionData | null>(null);

  const [menu, setMenu] = useState<{ x: number, y: number, nodeId?: string } | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const { project } = useReactFlow();

  useEffect(() => {
    if (!loading) {
      setNodes(graphData.nodes);
      setEdges(graphData.edges);
      setLastEvent('GRAPH_LOADED_SUCCESS');
    }
  }, [loading, graphData, setNodes, setEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === 'decision') {
      setLastEvent(`DECISION_NODE_SELECTED: ${node.data.label}`);
      const decisionData: DecisionData = {
        id: node.id,
        question: node.data.question,
        options: node.data.options,
      };
      setActiveDecision(decisionData);
      setInspectorOpen(true);
    } else {
      setLastEvent(`TASK_INSPECT: ${node.data.label}`);
      setInspectorOpen(false);
    }
  }, [setNodes]);

  const handleContextSelect = (fileName: string) => {
    setLastEvent(`NAVIGATING_TO_CONTEXT: ${fileName}`);
  };

  const onPaneContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    if (!ref.current) return;
    const pane = ref.current.getBoundingClientRect();
    setMenu({
      x: event.clientX - pane.left,
      y: event.clientY - pane.top,
    });
  }, [ref, setMenu]);

  const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    if (!ref.current) return;
    const pane = ref.current.getBoundingClientRect();
    setMenu({
      x: event.clientX - pane.left,
      y: event.clientY - pane.top,
      nodeId: node.id,
    });
  }, [ref, setMenu]);

  const addNode = (type: 'task' | 'decision') => {
    if (!menu) return;
    const { x, y } = menu;
    const position = project({ x, y });
    const newNode = {
      id: `new-${+new Date()}`,
      type,
      position,
      data: { label: `New ${type}` }
    };
    setNodes((nds) => nds.concat(newNode));
    setMenu(null);
  };
  
  const expandNode = (nodeId: string) => {
    setLastEvent(`AI_EXPANDING_NODE: ${nodeId}...`);
    // Simulate backend call to roadmap_service.expand_node
    setTimeout(() => {
      const parentNode = nodes.find(n => n.id === nodeId);
      if (!parentNode) return;
      
      const subNodes = [
        { id: `sub-${nodeId}-1`, label: 'Sub-task A', node_type: 'task', metadata: { icon: 'Default' }},
        { id: `sub-${nodeId}-2`, label: 'Sub-task B', node_type: 'task', metadata: { icon: 'Default' }},
      ];

      const newFlowNodes = subNodes.map((sn, i) => ({
        id: sn.id,
        type: 'task',
        position: { x: parentNode.position.x - 75 + (i * 150), y: parentNode.position.y + 120 },
        data: { label: sn.label, icon: ICONS.Default }
      }));

      const newFlowEdges = subNodes.map(sn => ({
        id: `e-${nodeId}-${sn.id}`,
        source: nodeId,
        target: sn.id,
        type: 'smoothstep',
        style: { stroke: '#00f0ff' }
      }));

      setNodes(nds => [...nds, ...newFlowNodes]);
      setEdges(eds => [...eds, ...newFlowEdges]);
      setLastEvent(`NODE ${nodeId} EXPANDED`);
    }, 1500);
    setMenu(null);
  };


  return (
    <div className="h-[calc(100vh-140px)] w-full flex flex-col gap-4 animate-fade-in relative" ref={ref}>
      <div className="flex justify-between items-end">
         <div>
            <h2 className="text-2xl font-mono text-white tracking-wide">PROJECT_ROADMAP</h2>
            <p className="text-gray-500 font-mono text-xs mt-1">DECISION_TREE_VISUALIZER</p>
         </div>
         <div className="bg-black/50 border border-white/10 px-3 py-1 rounded text-[10px] font-mono text-amber">
            EVENT_LOG: {lastEvent}
         </div>
      </div>

      <div className="flex-1 border border-white/10 rounded-xl overflow-hidden bg-void relative shadow-2xl">
         <div className="absolute inset-0 pointer-events-none z-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.1) 1px, transparent 0)', backgroundSize: '20px 20px' }}></div>
        
        {loading && <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-50 text-cyan font-mono animate-pulse">LOADING_GRAPH_DATA...</div>}

         <ReactFlow
           nodes={nodes}
           edges={edges}
           onNodesChange={onNodesChange}
           onEdgesChange={onEdgesChange}
           onNodeClick={onNodeClick}
           onPaneContextMenu={onPaneContextMenu}
           onNodeContextMenu={onNodeContextMenu}
           nodeTypes={nodeTypes}
           fitView
           minZoom={0.5}
           proOptions={{ hideAttribution: true }}
         >
           <Background color="#111" gap={20} size={1} />
           <Controls className="bg-panel border border-white/10 text-white fill-white" />
         </ReactFlow>
        
        <AnimatePresence>
        {menu && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={{ left: menu.x, top: menu.y }}
            className="absolute z-50 bg-panel border border-white/10 rounded-md shadow-lg p-2 font-mono text-xs"
            onMouseLeave={() => setMenu(null)}
          >
            <div className="flex items-center justify-between px-2 pb-1 mb-1 border-b border-white/10">
              <span className="text-gray-500">Actions</span>
              <button onClick={() => setMenu(null)} className="text-gray-600 hover:text-white p-1 -mr-1"><X size={12} /></button>
            </div>
            <button onClick={() => addNode('task')} className="w-full text-left flex items-center gap-2 p-2 rounded hover:bg-white/5 transition-colors">
              <Plus size={12} /> Add Task Node
            </button>
            <button onClick={() => addNode('decision')} className="w-full text-left flex items-center gap-2 p-2 rounded hover:bg-white/5 transition-colors">
              <Plus size={12} /> Add Decision Node
            </button>
            {menu.nodeId && (
              <button onClick={() => expandNode(menu.nodeId!)} className="w-full text-left flex items-center gap-2 p-2 rounded hover:bg-cyan/10 text-cyan transition-colors">
                <BrainCircuit size={12} /> Auto-Expand Branch
              </button>
            )}
          </motion.div>
        )}
        </AnimatePresence>

         <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur border border-white/10 p-3 rounded-lg z-10">
            <div className="text-[10px] font-mono text-gray-500 uppercase mb-2">Map Legend</div>
            <div className="flex flex-col gap-2">
               <div className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-cyan/20 border border-cyan/50"></div><span className="text-[10px] font-mono text-gray-300">Task</span></div>
               <div className="flex items-center gap-2"><div className="w-3 h-3 rotate-45 bg-amber/20 border border-amber/50 ml-0.5"></div><span className="text-[10px] font-mono text-gray-300 ml-1">Decision</span></div>
            </div>
         </div>
         
         <OptionInspector 
            isOpen={inspectorOpen} 
            data={activeDecision} 
            onClose={() => setInspectorOpen(false)} 
            onContextSelect={handleContextSelect}
            onCommit={(option) => {
              setLastEvent(`COMMITTING_TO_OPTION: ${option.label}`);
              // Simulate backend job
              setTimeout(() => {
                setLastEvent(`JOB_SUCCESS: Scaffolding for ${option.label} complete.`);
              }, 2000);
              setInspectorOpen(false);
            }}
         />
      </div>
    </div>
  );
};

// Need to wrap DecisionFlowMap with ReactFlowProvider where it's used
// For now, let's assume App.tsx will be updated to do this.
// We can create a wrapper here for completeness.
const DecisionFlowMapWrapper = () => (
  <ReactFlowProvider>
    <DecisionFlowMap />
  </ReactFlowProvider>
);

export { DecisionFlowMapWrapper as DecisionFlowMap };

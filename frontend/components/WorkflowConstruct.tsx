
import React, { useCallback, useState, useEffect } from 'react';
import ReactFlow, { 
  Node, 
  Edge, 
  Handle, 
  Position, 
  Background, 
  useNodesState, 
  useEdgesState, 
  MarkerType,
  EdgeProps,
  getBezierPath,
  BaseEdge
} from 'reactflow';
import { 
  Brain, 
  Search, 
  Database, 
  GitMerge, 
  Terminal, 
  CheckCircle, 
  Flag, 
  AlertOctagon, 
  Layers,
  Scale,
  X,
  Copy,
  Check,
  Code
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

// --- Types ---

export interface WorkflowConstructProps {
  graphState: {
    nodes: Node[];
    edges: Edge[];
    activeNodeId: string | null;
    visitedNodeIds: string[];
  };
}

// --- Icons Mapping ---
const getIconForLabel = (label: string) => {
  const l = label.toLowerCase();
  if (l.includes('search') || l.includes('retrieve')) return <Search size={14} />;
  if (l.includes('grade') || l.includes('critique')) return <Scale size={14} />;
  if (l.includes('generate') || l.includes('draft')) return <Brain size={14} />;
  if (l.includes('router') || l.includes('decision')) return <GitMerge size={14} />;
  if (l.includes('start')) return <Terminal size={14} />;
  if (l.includes('end') || l.includes('final')) return <Flag size={14} />;
  if (l.includes('error')) return <AlertOctagon size={14} />;
  return <Layers size={14} />;
};

// --- Mock Data Generator for Inspection ---
const generateMockData = (nodeId: string, label: string) => {
  const timestamp = new Date().toISOString();
  const l = label.toLowerCase();

  if (l.includes('start')) {
    return {
      step: 'initialization',
      timestamp,
      inputs: { query: "Analyze optimization protocols for Project Titan" },
      metadata: { session_id: "sess_8921", user_tier: "admin" }
    };
  }
  if (l.includes('retrieve')) {
    return {
      step: 'vector_retrieval',
      timestamp,
      index: "nexus_core_v4",
      embedding_model: "text-embedding-3-large",
      results_count: 5,
      top_score: 0.92,
      sources: ["Project_Titan_Specs.pdf", "auth_middleware.rs"]
    };
  }
  if (l.includes('grade')) {
    return {
      step: 'relevance_grading',
      timestamp,
      model: "gpt-4-turbo",
      evaluations: [
        { doc_id: "doc_1", relevant: true, score: 0.95 },
        { doc_id: "doc_2", relevant: true, score: 0.88 },
        { doc_id: "doc_3", relevant: false, score: 0.42, reason: "Off-topic" }
      ],
      passed_docs: 2
    };
  }
  if (l.includes('web_search')) {
    return {
      step: 'external_tool_execution',
      tool: "google_search",
      query: "Project Titan liquid cooling specs",
      latency_ms: 450,
      results: [
        { title: "Liquid Cooling in High Density Compute", url: "https://..." },
        { title: "Titan Protocol RFC", url: "https://..." }
      ]
    };
  }
  if (l.includes('generate')) {
    return {
      step: 'llm_generation',
      model: "llama-3-70b-instruct",
      temperature: 0.7,
      prompt_tokens: 1405,
      completion_tokens: 240,
      finish_reason: "stop",
      output_preview: "Based on the retrieved context, Project Titan requires active liquid cooling..."
    };
  }
  if (l.includes('final')) {
    return {
      step: 'workflow_complete',
      status: 'success',
      total_duration_ms: 2450,
      cost_estimate: "$0.042"
    };
  }
  
  return {
    step: 'generic_process',
    id: nodeId,
    status: 'executed',
    payload: { data: "sample_buffer_content", size_kb: 12 }
  };
};

// --- Custom Node Component ---
const CyberNode = ({ data, id, selected }: { data: any, id: string, selected: boolean }) => {
  const { label, isActive, isVisited } = data;

  // Visual State Logic
  let borderColor = 'border-white/10';
  let textColor = 'text-gray-500';
  let bgColor = 'bg-black/80';
  let shadow = '';
  let iconColor = 'text-gray-600';

  if (isActive) {
    borderColor = 'border-cyan';
    textColor = 'text-cyan';
    bgColor = 'bg-cyan/5';
    shadow = 'shadow-[0_0_20px_rgba(0,240,255,0.4)]';
    iconColor = 'text-cyan';
  } else if (isVisited) {
    borderColor = 'border-green-500/50';
    textColor = 'text-green-400';
    bgColor = 'bg-green-900/10';
    shadow = 'shadow-[0_0_10px_rgba(34,197,94,0.2)]';
    iconColor = 'text-green-500';
  } else if (selected) {
    borderColor = 'border-purple';
    textColor = 'text-purple';
    shadow = 'shadow-[0_0_15px_rgba(189,0,255,0.4)]';
    iconColor = 'text-purple';
  }

  return (
    <div className={`
      relative min-w-[180px] px-4 py-3 rounded-lg border-2 backdrop-blur-md transition-all duration-300
      ${borderColor} ${textColor} ${bgColor} ${shadow}
      ${isActive ? 'animate-pulse' : ''}
      hover:border-white/30 cursor-pointer
    `}>
      {/* Handles */}
      <Handle type="target" position={Position.Top} className="!bg-white/20 !w-2 !h-2 !rounded-sm opacity-50" />
      <Handle type="source" position={Position.Bottom} className="!bg-white/20 !w-2 !h-2 !rounded-sm opacity-50" />

      <div className="flex items-center gap-3">
        <div className={`p-1.5 rounded bg-black/50 border border-white/5 ${iconColor}`}>
          {getIconForLabel(label)}
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-widest opacity-50 font-mono">STEP</span>
          <span className="font-mono text-xs font-bold tracking-tight">{label}</span>
        </div>
      </div>
      
      {/* Decorative Corner Accents */}
      <div className={`absolute top-0 left-0 w-2 h-2 border-t border-l ${isActive ? 'border-cyan' : 'border-transparent'}`}></div>
      <div className={`absolute bottom-0 right-0 w-2 h-2 border-b border-r ${isActive ? 'border-cyan' : 'border-transparent'}`}></div>
    </div>
  );
};

// --- Custom Edge Component ---
const CyberEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data
}: EdgeProps) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isActive = data?.isActive;
  const isTraversed = data?.isTraversed;

  return (
    <>
      {/* Background path for visibility */}
      <BaseEdge path={edgePath} style={{ stroke: '#333', strokeWidth: 1 }} />
      
      {/* Animated Foreground Path */}
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          strokeWidth: isActive ? 2 : isTraversed ? 1.5 : 1,
          stroke: isActive ? '#00f0ff' : isTraversed ? '#22c55e' : '#333',
          strokeDasharray: isActive || isTraversed ? '5, 5' : '0',
          animation: isActive ? 'dashdraw 0.5s linear infinite' : isTraversed ? 'dashdraw 3s linear infinite' : 'none',
          opacity: isActive || isTraversed ? 1 : 0.3,
          ...style,
        }}
      />
      <style>{`
        @keyframes dashdraw {
          from { stroke-dashoffset: 10; }
          to { stroke-dashoffset: 0; }
        }
      `}</style>
    </>
  );
};

const nodeTypes = {
  cyber: CyberNode,
};

const edgeTypes = {
  cyber: CyberEdge,
};

// --- Main Component ---
export const WorkflowConstruct: React.FC<WorkflowConstructProps> = ({ graphState }) => {
  const { nodes, edges, activeNodeId, visitedNodeIds } = graphState;

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [drawerData, setDrawerData] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);

  // Process nodes to inject visual state
  const processedNodes = nodes.map(node => ({
    ...node,
    type: 'cyber', // Force our custom type
    data: {
      ...node.data,
      isActive: node.id === activeNodeId,
      isVisited: visitedNodeIds.includes(node.id)
    }
  }));

  // Process edges to inject visual state
  const processedEdges = edges.map(edge => {
    const isTargetActive = edge.target === activeNodeId;
    const isTraversed = visitedNodeIds.includes(edge.source) && (visitedNodeIds.includes(edge.target) || edge.target === activeNodeId);

    return {
      ...edge,
      type: 'cyber',
      animated: false, 
      data: {
        isActive: isTargetActive,
        isTraversed: isTraversed
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: isTargetActive ? '#00f0ff' : isTraversed ? '#22c55e' : '#333',
      }
    };
  });

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    const mockState = generateMockData(node.id, node.data.label);
    setDrawerData({
      id: node.id,
      label: node.data.label,
      status: node.id === activeNodeId ? 'RUNNING' : visitedNodeIds.includes(node.id) ? 'COMPLETED' : 'PENDING',
      state: mockState
    });
  }, [activeNodeId, visitedNodeIds]);

  const closeDrawer = () => {
    setSelectedNodeId(null);
    setDrawerData(null);
    setCopied(false);
  };

  const copyToClipboard = () => {
    if (drawerData?.state) {
      navigator.clipboard.writeText(JSON.stringify(drawerData.state, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="w-full h-full rounded-xl overflow-hidden relative border border-white/10 bg-void flex">
      
      {/* Hexagonal Grid Background (CSS) */}
      <div className="absolute inset-0 pointer-events-none z-0 opacity-10"
           style={{
             backgroundImage: `url("data:image/svg+xml,%3Csvg width='24' height='40' viewBox='0 0 24 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 40c5.523 0 10-4.477 10-10V10c0-5.523 4.477-10 10-10s10 4.477 10 10v20c0 5.523-4.477 10-10 10S0 35.523 0 30V40z' fill='%23ffffff' fill-opacity='0.1' fill-rule='evenodd'/%3E%3C/svg%3E")`,
             backgroundSize: '30px 50px'
           }}
      ></div>

      <div className="flex-1 h-full relative">
        <ReactFlow
          nodes={processedNodes}
          edges={processedEdges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.5}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        >
          <Background color="#111" gap={20} size={1} />
        </ReactFlow>
      </div>

      {/* Overlay Status Badge */}
      <div className="absolute top-4 left-4 z-10 bg-black/60 backdrop-blur border border-white/10 rounded-lg p-3">
         <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">Agent Status</div>
         <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${activeNodeId ? 'bg-cyan animate-pulse' : 'bg-gray-600'}`}></div>
            <span className={`text-xs font-mono font-bold ${activeNodeId ? 'text-white' : 'text-gray-400'}`}>
               {activeNodeId ? `EXECUTING: ${activeNodeId.toUpperCase()}` : 'IDLE'}
            </span>
         </div>
      </div>

      {/* Inspection Drawer */}
      <AnimatePresence>
        {selectedNodeId && drawerData && (
          <motion.div 
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute top-4 right-4 bottom-4 w-[400px] bg-panel/90 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl z-50 flex flex-col overflow-hidden"
          >
             {/* Header */}
             <div className="p-4 border-b border-white/10 bg-black/40 flex justify-between items-center">
                <div className="flex items-center gap-3">
                   <div className={`p-2 rounded bg-white/5 border border-white/10 ${drawerData.status === 'RUNNING' ? 'text-cyan' : drawerData.status === 'COMPLETED' ? 'text-green-500' : 'text-gray-400'}`}>
                      {getIconForLabel(drawerData.label)}
                   </div>
                   <div>
                      <h3 className="font-mono font-bold text-sm text-white">{drawerData.label}</h3>
                      <div className="flex items-center gap-2">
                         <div className={`w-1.5 h-1.5 rounded-full ${drawerData.status === 'RUNNING' ? 'bg-cyan animate-pulse' : drawerData.status === 'COMPLETED' ? 'bg-green-500' : 'bg-gray-500'}`}></div>
                         <span className="text-[10px] font-mono text-gray-400 tracking-wider">{drawerData.status}</span>
                      </div>
                   </div>
                </div>
                <button onClick={closeDrawer} className="text-gray-500 hover:text-white transition-colors">
                   <X size={20} />
                </button>
             </div>

             {/* Content */}
             <div className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-4 custom-scrollbar">
                
                {/* Data View */}
                <div className="relative group">
                   <div className="flex justify-between items-center mb-2">
                      <label className="text-[10px] uppercase tracking-widest text-gray-500 flex items-center gap-2">
                         <Code size={12} /> State Payload
                      </label>
                      <button 
                        onClick={copyToClipboard}
                        className={`flex items-center gap-1.5 px-2 py-1 rounded border transition-all text-[10px] uppercase font-bold
                          ${copied 
                            ? 'bg-green-500/20 border-green-500 text-green-500' 
                            : 'bg-white/5 border-white/10 text-cyan hover:bg-cyan/10 hover:border-cyan hover:shadow-[0_0_10px_rgba(0,240,255,0.3)]'}
                        `}
                      >
                         {copied ? <Check size={10} /> : <Copy size={10} />}
                         {copied ? 'COPIED' : 'COPY JSON'}
                      </button>
                   </div>
                   
                   <div className="relative">
                      {/* Glow effect behind code block */}
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan/20 to-purple/20 rounded blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                      
                      <pre className="relative p-4 bg-black/80 rounded border border-white/10 text-gray-300 overflow-x-auto shadow-inner">
                         <code>{JSON.stringify(drawerData.state, null, 2)}</code>
                      </pre>
                   </div>
                </div>

                {/* Additional Metadata / Logs */}
                <div className="space-y-2">
                   <label className="text-[10px] uppercase tracking-widest text-gray-500">Execution Metadata</label>
                   <div className="grid grid-cols-2 gap-2">
                      <div className="bg-white/5 p-2 rounded border border-white/10">
                         <div className="text-[9px] text-gray-500">Node ID</div>
                         <div className="text-white truncate" title={drawerData.id}>{drawerData.id}</div>
                      </div>
                      <div className="bg-white/5 p-2 rounded border border-white/10">
                         <div className="text-[9px] text-gray-500">Latency</div>
                         <div className="text-cyan">42ms</div>
                      </div>
                   </div>
                </div>

             </div>

             {/* Footer */}
             <div className="p-3 border-t border-white/10 bg-black/20 text-[9px] text-gray-600 text-center font-mono">
                LANGGRAPH_DEBUG_VIEW // V3.1
             </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
};

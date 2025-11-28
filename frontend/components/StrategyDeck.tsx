import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactFlow, {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  Background,
  Controls,
  MiniMap,
  NodeProps,
  Handle,
  Position,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Lightbulb, Terminal, BrainCircuit, Mic, Sparkles, Quote, Play } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';

// --- Types ---
interface ChatLog {
  id: string;
  user: string;
  timestamp: string;
  message: string;
  containsIdeaId?: string;
}

type IdeaType = 'feature' | 'infra' | 'unknown' | 'project' | 'raw';

interface Idea {
  id: string;
  type: IdeaType;
  summary: string;
  sourceContext?: string;
  sourceUser?: string;
  confidence: number;
}

type IdeaNodeData = {
  idea: Idea;
};

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
  { id: 'i1', type: 'infra', summary: 'Implement HNSW indexing on Qdrant cluster to resolve vector search latency.', sourceContext: "We should probably implement HNSW indexing on the Qdrant cluster.", sourceUser: 'mike_dev', confidence: 0.95 },
  { id: 'i2', type: 'feature', summary: 'Automated PR description generator using diff analysis.', sourceContext: "build a tool that generates PR descriptions from diffs automatically.", sourceUser: 'mike_dev', confidence: 0.88 },
  { id: 'i3', type: 'project', summary: 'Voice-to-Task extraction for engineering meetings.', sourceContext: "listen to voice meetings and extract tasks directly.", sourceUser: 'dave_arch', confidence: 0.72 },
];

// --- Custom Node Component ---
const IdeaNode: React.FC<NodeProps<IdeaNodeData>> = ({ data, selected }) => {
  const { idea } = data;

  const getTypeStyles = (type: IdeaType) => {
    switch (type) {
      case 'feature': return 'bg-cyan/20 border-cyan text-cyan';
      case 'infra': return 'bg-amber/20 border-amber text-amber';
      case 'project': return 'bg-purple/20 border-purple text-purple';
      case 'raw': return 'bg-gray-500/20 border-gray-500 text-gray-300';
      default: return 'bg-gray-400/20 border-gray-400 text-gray-400';
    }
  };

  return (
    <div
      className={`
        w-64 rounded-lg shadow-lg font-sans transition-all duration-200
        ${selected ? 'ring-2 ring-white ring-offset-2 ring-offset-black' : ''}
        ${getTypeStyles(idea.type).split(' ')[0]}
        border ${getTypeStyles(idea.type).split(' ')[1]}
      `}
      style={{
        boxShadow: `0 0 20px ${getTypeStyles(idea.type).split(' ')[0].replace('/20', '/40')}`
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />
      <div className="p-4 bg-black/50 rounded-lg">
        <div className="flex justify-between items-start mb-2">
          <div className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getTypeStyles(idea.type)}`}>
            {idea.type}
          </div>
          <div className="text-[10px] font-mono text-gray-500 flex items-center gap-1">
            CONF: <span className="text-white">{(idea.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>

        <p className="text-sm text-white mb-3 leading-snug">{idea.summary}</p>

        {idea.sourceContext && (
          <div className="bg-black/40 rounded p-2 border border-white/5 relative text-xs">
            <Quote size={10} className="absolute top-1.5 left-1.5 text-gray-600" />
            <p className="text-gray-400 font-mono italic pl-3">
              "{idea.sourceContext}"
            </p>
            <div className="mt-1 text-[9px] text-gray-600 text-right font-mono">
              — @{idea.sourceUser}
            </div>
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-500" />
    </div>
  );
};

const nodeTypes = {
  ideaNode: IdeaNode,
};

// --- Main Component ---
export const StrategyDeck: React.FC = () => {
  const [nodes, setNodes] = useState<Node<IdeaNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [visibleLogs, setVisibleLogs] = useState<ChatLog[]>([]);
  const [scanIndex, setScanIndex] = useState(-1);
  const [statusText, setStatusText] = useState('READY_TO_SCAN');
  
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );
  const onConnect: OnConnect = useCallback(
    (connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  const reactFlowInstance = useReactFlow();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let delay = 0;
    MOCK_LOGS.forEach((log) => {
      setTimeout(() => setVisibleLogs(prev => [...prev, log]), delay);
      delay += 150;
    });
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleLogs]);

  const addIdeaNode = (idea: Idea) => {
    const newNode: Node<IdeaNodeData> = {
      id: idea.id,
      type: 'ideaNode',
      position: {
        x: Math.random() * 400 - 200,
        y: Math.random() * 400 - 200,
      },
      data: { idea },
    };
    setNodes((nds) => [...nds, newNode]);
  };
  
  const runAnalysis = () => {
    if (isAnalyzing) return;
    setIsAnalyzing(true);
    setNodes([]); // Clear existing nodes
    setEdges([]);
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
      if (currentIndex % 2 === 0) setStatusText('READING_STREAM...');
      if (currentLog.containsIdeaId) {
        setStatusText('SIGNAL_DETECTED');
        const idea = EXTRACTED_IDEAS.find(i => i.id === currentLog.containsIdeaId);
        if (idea) {
          setTimeout(() => addIdeaNode(idea), 400);
        }
      }
      currentIndex++;
    }, 800);
  };
  
  const addVoiceIdea = () => {
    // Stub function for voice input
    const newIdea: Idea = {
      id: `raw-${Date.now()}`,
      type: 'raw',
      summary: 'New voice-captured idea...',
      confidence: 0.5,
      sourceUser: 'voice_input',
    };
    addIdeaNode(newIdea);
  };

  const synthesizeCluster = () => {
    // Stub for synthesizing selected nodes
    const selectedNodes = reactFlowInstance.getNodes().filter(n => n.selected);
    if (selectedNodes.length < 2) {
      alert("Please select 2 or more ideas to synthesize.");
      return;
    }
    console.log("Synthesizing epic from:", selectedNodes.map(n => n.data.idea.summary));
    // Here you would call the backend with the selected ideas
    alert(`Synthesizing ${selectedNodes.length} ideas into a new Epic/Feature ticket. (Backend call stub)`);
  };

  return (
    <div className="h-[calc(100vh-140px)] w-full flex gap-6 animate-fade-in pb-4">
      <div className="w-1/3 flex flex-col gap-4">
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
              <Terminal className="text-gray-400" />
              RAW_INTELLIGENCE
            </h2>
            <p className="text-gray-500 font-mono text-xs mt-1">SOURCE: ENGINEERING_CHAT_LOGS_V2.DB</p>
          </div>
          <NeonButton variant="cyan" onClick={runAnalysis} disabled={isAnalyzing} icon={<Play size={14} />}>
            {isAnalyzing ? 'SCANNING...' : 'RUN_ANALYSIS'}
          </NeonButton>
        </div>
        <GlassCard variant="void" className="flex-1 !p-0 overflow-hidden relative border-opacity-50">
          {isAnalyzing && (
            <div className="absolute left-0 right-0 h-[2px] bg-cyan/50 z-20 shadow-[0_0_15px_cyan]" style={{ top: `${(scanIndex / MOCK_LOGS.length) * 100}%`, transition: 'top 0.8s linear' }} />
          )}
          <div className="absolute top-2 right-2 z-20">
            <span className={`text-[10px] font-mono font-bold px-2 py-1 rounded bg-black/80 border border-white/10 ${isAnalyzing ? 'text-cyan animate-pulse' : 'text-gray-500'}`}>
              {statusText}
            </span>
          </div>
          <div className="p-4 h-full overflow-y-auto font-mono text-sm space-y-3 scrollbar-hide" ref={scrollRef}>
            {visibleLogs.map((log, index) => {
              const isScanned = index === scanIndex;
              const hasIdea = log.containsIdeaId && (index <= scanIndex);
              return (
                <div key={log.id} className={`relative pl-3 py-1 transition-all duration-300 ${isScanned ? 'bg-cyan/5' : ''} ${hasIdea ? 'border-l-2 border-amber' : 'border-l-2 border-transparent'}`}>
                  <div className="flex items-baseline gap-2 text-xs text-gray-500 mb-0.5">
                    <span>{log.timestamp}</span>
                    <span className={`font-bold ${hasIdea ? 'text-amber' : 'text-gray-400'}`}>@{log.user}</span>
                  </div>
                  <div className={`text-gray-300 ${isScanned ? 'text-white' : ''}`}>{log.message}</div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      </div>

      <div className="w-2/3 flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
            <BrainCircuit className="text-purple" />
            STRATEGY_CANVAS
          </h2>
          <div className="flex items-center gap-2">
            <NeonButton variant="secondary" onClick={addVoiceIdea} icon={<Mic size={14} />}>
              VOICE_INPUT
            </NeonButton>
            <NeonButton variant="primary" onClick={synthesizeCluster} icon={<Sparkles size={14} />}>
              SYNTHESIZE_CLUSTER
            </NeonButton>
          </div>
        </div>
        <GlassCard className="flex-1 relative border-dashed">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            className="bg-transparent"
          >
            <Background color="#444" gap={16} />
            <Controls className="text-white" />
            <MiniMap nodeColor={n => n.data.idea.type === 'feature' ? '#00f0ff' : n.data.idea.type === 'infra' ? '#ffbf00' : '#8A2BE2'} pannable />
          </ReactFlow>
          {nodes.length === 0 && !isAnalyzing && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500 gap-4 pointer-events-none">
               <Lightbulb size={32} className="opacity-50" />
               <div className="text-center">
                 <div className="text-sm font-mono">IDEATION_CANVAS_EMPTY</div>
                 <div className="text-xs mt-1">Run analysis or add ideas to begin.</div>
               </div>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
};

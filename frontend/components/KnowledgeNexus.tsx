import React, { useRef, useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { X, FileText, GitCommit, MessageSquare, ExternalLink } from 'lucide-react';
import { NeonButton } from './NeonButton';
import { useKnowledgeGraph } from '@src/hooks/useKnowledgeGraph';
import { useCurrentProject } from '@src/hooks/useProjects';

// Types for our graph
type NodeType = 'pdf' | 'repo' | 'chat';

interface Node {
  id: string;
  name: string;
  type: NodeType;
  val: number; // size
  color: string;
  summary?: string;
  meta?: string;
}

interface Link {
  source: string;
  target: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

export const KnowledgeNexus: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const { project: currentProject } = useCurrentProject();
  const { data: graphData, isLoading, error } = useKnowledgeGraph(currentProject?.id);

  // Handle Resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };

    window.addEventListener('resize', updateDimensions);
    updateDimensions();

    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Transform API data to graph format
  const transformedData = React.useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };

    const nodes: Node[] = graphData.nodes.map(node => ({
      id: node.id,
      name: node.title || node.id,
      type: node.type as NodeType,
      val: 5 + (node.summary?.length || 0) / 100, // Size based on content
      color: node.type === 'pdf' ? '#00f0ff' : node.type === 'repo' ? '#ffbf00' : '#bd00ff',
      meta: `ID: ${node.id}`,
      summary: node.summary
    }));

    const links: Link[] = graphData.edges.map(edge => ({
      source: edge.source,
      target: edge.target
    }));

    return { nodes, links };
  }, [graphData]);

  // Show loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan mx-auto mb-2"></div>
          <p className="text-gray-400 font-mono text-sm">Loading knowledge graph...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-red-400 mb-2">Failed to load knowledge graph</div>
          <p className="text-gray-400 font-mono text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  // Show empty state
  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-gray-400 mb-2">No knowledge nodes found</div>
          <p className="text-gray-500 font-mono text-sm">Ingest some documents to see the knowledge graph</p>
        </div>
      </div>
    );
  }

  // Custom Node Rendering
  const paintNode = (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const { type, x, y, color } = node;
    const size = 6;
    
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 10;
    
    ctx.beginPath();
    if (type === 'pdf') {
      // Circle
      ctx.arc(x, y, size, 0, 2 * Math.PI, false);
    } else if (type === 'repo') {
      // Square
      ctx.rect(x - size, y - size, size * 2, size * 2);
    } else if (type === 'chat') {
      // Triangle
      ctx.moveTo(x, y - size);
      ctx.lineTo(x + size, y + size);
      ctx.lineTo(x - size, y + size);
      ctx.closePath();
    }
    ctx.fill();

    // Reset shadow for text
    ctx.shadowBlur = 0;
    
    // Draw Label if hovered or selected (simplified for this demo: always draw small label)
    if (globalScale > 1.5 || node === selectedNode) {
        ctx.font = '3px "JetBrains Mono"';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = 'white';
        ctx.fillText(node.name.substring(0, 10), x, y + size + 4);
    }
  };

  return (
    <div className="relative w-full h-full min-h-[600px] flex overflow-hidden animate-hologram bg-void/50 rounded-xl border border-white/5">
      
      {/* Graph Container */}
      <div className="flex-1 relative" ref={containerRef}>
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={transformedData}
          nodeLabel="name"
          nodeColor="color"
          linkColor={() => 'rgba(0, 240, 255, 0.15)'}
          linkWidth={1}
          nodeCanvasObject={paintNode}
          onNodeClick={(node) => {
            setSelectedNode(node as Node);
            // Center camera on node
            graphRef.current?.centerAt(node.x, node.y, 1000);
            graphRef.current?.zoom(3, 2000);
          }}
          backgroundColor="rgba(0,0,0,0)"
          enableNodeDrag={false}
          cooldownTicks={100}
        />
        
        {/* Overlay Grid lines for decoration */}
        <div className="absolute inset-0 pointer-events-none opacity-20"
             style={{
               backgroundImage: 'linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)',
               backgroundSize: '100px 100px'
             }}>
        </div>
      </div>

      {/* Quick-View Glass Drawer */}
      <div className={`
        absolute top-4 right-4 bottom-4 w-80 bg-panel/90 backdrop-blur-xl border-l border-white/10 shadow-2xl 
        transform transition-transform duration-500 ease-out z-20 rounded-xl overflow-hidden flex flex-col
        ${selectedNode ? 'translate-x-0' : 'translate-x-[120%]'}
      `}>
        {selectedNode && (
          <>
            {/* Drawer Header */}
            <div className={`p-4 border-b border-white/10 bg-gradient-to-r ${
                selectedNode.type === 'pdf' ? 'from-cyan/20' : 
                selectedNode.type === 'repo' ? 'from-amber/20' : 'from-purple/20'
            } to-transparent`}>
              <div className="flex justify-between items-start mb-2">
                 <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-gray-400">
                    {selectedNode.type === 'pdf' && <FileText size={14} className="text-cyan"/>}
                    {selectedNode.type === 'repo' && <GitCommit size={14} className="text-amber"/>}
                    {selectedNode.type === 'chat' && <MessageSquare size={14} className="text-purple"/>}
                    {selectedNode.type.toUpperCase()} NODE
                 </div>
                 <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-white transition-colors">
                   <X size={18} />
                 </button>
              </div>
              <h3 className="font-bold text-lg leading-tight text-white mb-1 truncate">{selectedNode.name}</h3>
              <p className="text-[10px] font-mono text-gray-400">{selectedNode.meta}</p>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 p-4 overflow-y-auto font-sans text-sm text-gray-300 space-y-4">
               <div>
                 <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Summary</h4>
                 <p className="leading-relaxed border-l-2 border-white/10 pl-3 italic">
                   {selectedNode.summary || "No summary available for this node data."}
                 </p>
               </div>
               
               <div className="space-y-2">
                 <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Connected Entities</h4>
                 <div className="flex flex-wrap gap-2">
                   {/* Mock connected entities */}
                   <span className="px-2 py-1 bg-white/5 rounded text-xs border border-white/10">Architecture</span>
                   <span className="px-2 py-1 bg-white/5 rounded text-xs border border-white/10">Neural Nets</span>
                   <span className="px-2 py-1 bg-white/5 rounded text-xs border border-white/10">VRAM</span>
                 </div>
               </div>
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-white/10 bg-black/20">
               <NeonButton 
                 variant={selectedNode.type === 'pdf' ? 'cyan' : selectedNode.type === 'repo' ? 'amber' : 'purple'} 
                 fullWidth 
                 className="text-xs"
                 icon={<ExternalLink size={14}/>}
               >
                 OPEN SOURCE
               </NeonButton>
            </div>
          </>
        )}
      </div>

    </div>
  );
};

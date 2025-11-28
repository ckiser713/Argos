import React, { useRef, useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { X, FileText, GitCommit, MessageSquare, ExternalLink, AlertCircle } from 'lucide-react';
import { NeonButton } from './NeonButton';
import { useKnowledgeGraph } from '@src/hooks/useKnowledgeGraph';
import { useCurrentProject } from '@src/hooks/useProjects';

// --- Configuration ---
const MAX_NODES_DISPLAY = 500;

// --- Types ---
type NodeType = 'pdf' | 'repo' | 'chat';
// ... (rest of the types)

export const KnowledgeNexus: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [totalNodeCount, setTotalNodeCount] = useState(0);

  const { project: currentProject } = useCurrentProject();
  // The hook would ideally accept a limit: useKnowledgeGraph(currentProject?.id, MAX_NODES_DISPLAY);
  const { data: graphData, isLoading, error } = useKnowledgeGraph(currentProject?.id);

  // ... (useEffect for resize)

  const transformedData = React.useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };

    const allNodes = graphData.nodes;
    setTotalNodeCount(allNodes.length);

    const nodes: Node[] = allNodes.slice(0, MAX_NODES_DISPLAY).map(node => ({
      id: node.id,
      name: node.title || node.id,
      type: node.type as NodeType,
      val: 5 + (node.summary?.length || 0) / 100,
      color: node.type === 'pdf' ? '#00f0ff' : node.type === 'repo' ? '#ffbf00' : '#bd00ff',
      meta: `ID: ${node.id}`,
      summary: node.summary
    }));

    // Filter links to only include those between displayed nodes
    const nodeIds = new Set(nodes.map(n => n.id));
    const links: Link[] = graphData.edges
      .filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
      .map(edge => ({
        source: edge.source,
        target: edge.target
      }));

    return { nodes, links };
  }, [graphData]);
  
  // ... (rest of the component logic)

  return (
    <div className="relative w-full h-full min-h-[600px] flex overflow-hidden animate-hologram bg-void/50 rounded-xl border border-white/5">
      
      {/* Graph Container */}
      <div className="flex-1 relative" ref={containerRef}>
        {/* Node Limit Warning */}
        {totalNodeCount > MAX_NODES_DISPLAY && (
          <div className="absolute top-4 left-4 z-10 bg-amber/10 border border-amber/50 text-amber font-mono text-xs px-3 py-2 rounded-lg flex items-center gap-2">
            <AlertCircle size={16} />
            Displaying top {MAX_NODES_DISPLAY} of {totalNodeCount} nodes. Zoom to filter.
          </div>
        )}

        <ForceGraph2D
          // ... (rest of the ForceGraph2D props)
        />
        
        {/* ... (rest of the component) */}
      </div>

      {/* ... (rest of the component) */}
    </div>
  );
};

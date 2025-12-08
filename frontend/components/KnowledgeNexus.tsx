import React, { useRef, useState, useEffect, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { X, AlertCircle } from 'lucide-react';
import { NeonButton } from './NeonButton';
import { useKnowledgeGraph } from '@src/hooks/useKnowledgeGraph';
import { useCurrentProject } from '@src/hooks/useProjects';
import type { KnowledgeNode, KnowledgeEdge } from '@src/domain/types';

const MAX_NODES_DISPLAY = 500;

type GraphNode = {
  id: string;
  name: string;
  kind: string;
  color: string;
  val: number;
  summary?: string;
};

type GraphLink = {
  source: string;
  target: string;
  label?: string;
};

const KIND_COLORS: Record<string, string> = {
  canonical_doc: '#00f0ff',
  chunk_cluster: '#ffbf00',
  idea: '#bd00ff',
  ticket: '#7c3aed',
  workflow: '#10b981',
  agent_run: '#22d3ee',
  decision: '#f97316',
};

function toGraphNode(node: KnowledgeNode): GraphNode {
  const color = KIND_COLORS[node.kind] ?? '#7dd3fc';
  const size = Math.max(4, Math.min(16, node.size || 6));
  return {
    id: node.id,
    name: node.label || node.id,
    kind: node.kind,
    color,
    val: size,
    summary: node.description,
  };
}

function toGraphLink(edge: KnowledgeEdge): GraphLink {
  return {
    source: edge.source,
    target: edge.target,
    label: edge.label || edge.kind,
  };
}

export const KnowledgeNexus: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [totalNodeCount, setTotalNodeCount] = useState(0);

  const { project: currentProject } = useCurrentProject();
  const projectId = currentProject?.id;
  const { data: graphData, isLoading, error } = useKnowledgeGraph(projectId, { view: 'default' });

  useEffect(() => {
    const resize = () => {
      if (!containerRef.current) return;
      const { clientWidth, clientHeight } = containerRef.current;
      setDimensions({ width: clientWidth, height: clientHeight });
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  const transformedData = useMemo(() => {
    if (!graphData) return { nodes: [] as GraphNode[], links: [] as GraphLink[] };
    const nodes = graphData.nodes.slice(0, MAX_NODES_DISPLAY).map(toGraphNode);
    setTotalNodeCount(graphData.nodes.length);
    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = graphData.edges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map(toGraphLink);
    return { nodes, links };
  }, [graphData]);

  if (!projectId) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 font-mono">
        Select a project to view Knowledge Nexus.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 font-mono">
        Loading knowledge graph...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400 font-mono">
        Failed to load knowledge graph
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[600px] flex overflow-hidden animate-hologram bg-void/50 rounded-xl border border-white/5">
      <div className="flex-1 relative" ref={containerRef}>
        {totalNodeCount > MAX_NODES_DISPLAY && (
          <div className="absolute top-4 left-4 z-10 bg-amber/10 border border-amber/50 text-amber font-mono text-xs px-3 py-2 rounded-lg flex items-center gap-2">
            <AlertCircle size={16} />
            Displaying top {MAX_NODES_DISPLAY} of {totalNodeCount} nodes. Zoom to filter.
          </div>
        )}

        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={{ nodes: transformedData.nodes, links: transformedData.links }}
          nodeLabel="name"
          nodeRelSize={6}
          nodeColor={(node: any) => node.color}
          linkColor={() => 'rgba(255,255,255,0.25)'}
          onNodeClick={(node: any) => setSelectedNode(node)}
          cooldownTicks={50}
          enableNodeDrag={false}
          nodeCanvasObject={(node: any, ctx) => {
            const label = node.name;
            const fontSize = 10;
            ctx.fillStyle = node.color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
            ctx.fill();
            ctx.font = `${fontSize}px Inter, monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillStyle = '#e5e7eb';
            ctx.fillText(label, node.x, node.y + node.val + 2);
          }}
        />
      </div>

      {selectedNode && (
        <div className="w-80 border-l border-white/10 bg-black/50 backdrop-blur-md p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-400 font-mono uppercase">Node</div>
              <div className="text-white font-semibold break-words">{selectedNode.name}</div>
            </div>
            <NeonButton variant="void" size="sm" icon={<X size={14} />} onClick={() => setSelectedNode(null)}>
              CLOSE
            </NeonButton>
          </div>
          <div className="text-xs text-gray-400 font-mono uppercase">Kind</div>
          <div className="font-mono text-sm text-cyan">{selectedNode.kind}</div>
          {selectedNode.summary && (
            <>
              <div className="text-xs text-gray-400 font-mono uppercase">Summary</div>
              <div className="text-sm text-gray-200 whitespace-pre-wrap">{selectedNode.summary}</div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

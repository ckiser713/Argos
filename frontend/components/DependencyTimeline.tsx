
import React, { useRef, useEffect, useState, useMemo } from 'react';
import { addDays, format, differenceInDays, startOfToday, isBefore, isAfter } from 'date-fns';
import { AlertTriangle, Lock, GitMerge, Layers, Clock } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';
import { useCurrentProject } from '@src/hooks/useProjects';
import { useRoadmap } from '@src/hooks/useRoadmap';
import { ErrorDisplay } from '@src/components/ErrorDisplay';

// --- Types ---

interface Task {
  id: string;
  label: string;
  start: Date;
  end: Date;
  clusterId: string;
  dependencies: string[]; // ids of tasks this one depends on
  status: 'pending' | 'active' | 'completed' | 'blocked';
}

interface Cluster {
  id: string;
  label: string;
  color: string;
}

// --- Helpers ---

const CELL_WIDTH = 60; // px per day
const ROW_HEIGHT = 60; // px per cluster row (or task spacing)
const HEADER_HEIGHT = 50;

export const DependencyTimeline: React.FC = () => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [hoveredTask, setHoveredTask] = useState<string | null>(null);
  const today = startOfToday();
  const { project } = useCurrentProject();
  const { data: roadmapData, isLoading, error, refetch } = useRoadmap(project?.id);

  const palette = ['#00E0FF', '#9b59b6', '#f39c12', '#e74c3c', '#2ecc71', '#1abc9c', '#e67e22'];

  const tasks: Task[] = useMemo(() => {
    if (!roadmapData?.nodes) return [];
    return roadmapData.nodes.map((node, idx) => {
      const clusterId = node.lane_id || node.status || 'unassigned';
      const deps = (roadmapData.edges || []).filter(e => e.to === node.id).map(e => e.from);
      const start = node.start_date ? new Date(node.start_date) : today;
      const end = node.target_date ? new Date(node.target_date) : addDays(start, 7);
      const status = (node.status as Task['status']) || 'pending';
      return {
        id: node.id,
        label: node.label || `Node ${idx + 1}`,
        start,
        end,
        clusterId,
        dependencies: deps,
        status,
      };
    });
  }, [roadmapData, today]);

  const clusters: Cluster[] = useMemo(() => {
    const unique = new Map<string, Cluster>();
    tasks.forEach((task, idx) => {
      if (!unique.has(task.clusterId)) {
        unique.set(task.clusterId, {
          id: task.clusterId,
          label: task.clusterId.toUpperCase(),
          color: palette[idx % palette.length],
        });
      }
    });
    return Array.from(unique.values());
  }, [tasks]);
  
  // Timeline Range: -7 days to +14 days
  const startDate = addDays(today, -7);
  const daysToShow = 21;
  const dates = Array.from({ length: daysToShow }, (_, i) => addDays(startDate, i));

  // Auto-scroll to "today" on mount
  useEffect(() => {
    if (scrollRef.current) {
      const todayOffset = 7 * CELL_WIDTH; // 7 days in
      scrollRef.current.scrollLeft = todayOffset - 200; // Center it a bit
    }
  }, []);

  // Calculate Positions
  const getX = (date: Date) => differenceInDays(date, startDate) * CELL_WIDTH;
  const getWidth = (start: Date, end: Date) => (differenceInDays(end, start) + 1) * CELL_WIDTH;
  
  // Group tasks by cluster for rendering rows
  const tasksByCluster = clusters.map(cluster => ({
    ...cluster,
    tasks: tasks.filter(t => t.clusterId === cluster.id)
  }));

  if (isLoading) {
    return <div className="text-gray-400 font-mono p-6">Loading dependency timeline...</div>;
  }

  if (error) {
    return (
      <div className="p-6">
        <ErrorDisplay error={error} title="Failed to load roadmap" onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-140px)] w-full flex flex-col gap-4 animate-fade-in pb-4">
      
      {/* Header Info */}
      <div className="flex justify-between items-end px-2">
        <div>
          <h2 className="text-2xl font-mono text-white tracking-wide flex items-center gap-3">
             <Clock className="text-cyan" />
             DEPENDENCY_MAP
          </h2>
          <p className="text-gray-500 font-mono text-xs mt-1">CROSS-PROJECT SIGNAL STREAMS // GANTT VIEW</p>
        </div>
        
        {/* PM Agent Trigger (Visual Only) */}
        <div className="flex items-center gap-4">
            <NeonButton variant="purple" className="text-xs" icon={<Layers size={14}/>}>
               RUN_GAP_ANALYSIS
            </NeonButton>
        </div>
      </div>

      {/* Main Timeline Container */}
      <div className="flex-1 relative border border-white/10 rounded-xl bg-black/60 backdrop-blur-xl overflow-hidden flex flex-col">
         
         {/* Top Date Header */}
         <div className="flex border-b border-white/10 bg-panel/80 h-[50px] shrink-0 sticky top-0 z-20" style={{ paddingLeft: '200px' }}>
             {/* Left sidebar spacer is 200px (cluster names) */}
             <div ref={scrollRef} className="flex overflow-hidden relative w-full h-full cursor-grab active:cursor-grabbing">
                {/* Render Dates */}
                <div className="flex absolute top-0 left-0 h-full" style={{ width: daysToShow * CELL_WIDTH }}>
                   {dates.map((date, i) => {
                     const isToday = differenceInDays(date, today) === 0;
                     const isPast = isBefore(date, today);
                     return (
                       <div 
                         key={i} 
                         className={`shrink-0 border-r border-white/5 flex flex-col justify-center items-center h-full relative group
                           ${isToday ? 'bg-cyan/5' : ''}
                         `}
                         style={{ width: CELL_WIDTH }}
                       >
                         <span className={`text-[10px] font-mono font-bold ${isToday ? 'text-cyan' : isPast ? 'text-gray-600' : 'text-gray-400'}`}>
                           {format(date, 'MMM dd')}
                         </span>
                         <span className={`text-[9px] font-mono ${isToday ? 'text-cyan/70' : 'text-gray-700'}`}>
                           {format(date, 'EEE')}
                         </span>
                         {isToday && <div className="absolute bottom-0 w-full h-[2px] bg-cyan shadow-[0_0_10px_cyan]"></div>}
                       </div>
                     );
                   })}
                </div>
             </div>
         </div>

         {/* Content Area */}
         <div className="flex-1 relative overflow-auto custom-scrollbar">
             
             {/* SVG Background (Seismic Noise) */}
             <div className="absolute inset-0 pointer-events-none opacity-20 z-0">
                <svg width="100%" height="100%">
                   <pattern id="grid" width={CELL_WIDTH} height={ROW_HEIGHT} patternUnits="userSpaceOnUse">
                      <path d={`M ${CELL_WIDTH} 0 L 0 0 0 ${ROW_HEIGHT}`} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
                   </pattern>
                   <rect width="100%" height="100%" fill="url(#grid)" />
                   
                   {/* "Seismic" line mock */}
                   <path 
                     d="M 0 300 Q 200 250 400 350 T 800 300 T 1200 320" 
                     fill="none" 
                     stroke="rgba(0, 240, 255, 0.1)" 
                     strokeWidth="2" 
                     className="animate-pulse"
                   />
                </svg>
             </div>

             {/* Content Layout */}
             <div className="relative min-w-[max-content]" style={{ width: 200 + (daysToShow * CELL_WIDTH) }}>
                 
                 {/* Clusters Rows */}
                 {tasksByCluster.map((cluster, cIndex) => (
                    <div key={cluster.id} className="flex border-b border-white/5 relative group hover:bg-white/5 transition-colors">
                       
                       {/* Left Sidebar Label */}
                       <div className="w-[200px] shrink-0 p-4 border-r border-white/10 flex flex-col justify-center sticky left-0 bg-panel/90 backdrop-blur z-10">
                          <span className="text-xs font-mono font-bold tracking-widest" style={{ color: cluster.color }}>
                            {cluster.label}
                          </span>
                          <span className="text-[10px] text-gray-500 font-mono mt-1">{cluster.tasks.length} ACTIVE SIGNALS</span>
                       </div>

                       {/* Task Track */}
                       <div className="relative h-[80px] w-full">
                          {cluster.tasks.map(task => {
                             const x = getX(task.start);
                             const w = getWidth(task.start, task.end);
                             const isHovered = hoveredTask === task.id;
                             const isDependency = hoveredTask && TASKS.find(t => t.id === hoveredTask)?.dependencies.includes(task.id);
                             
                             return (
                               <div
                                 key={task.id}
                                 className="absolute top-1/2 -translate-y-1/2 z-10"
                                 style={{ left: x, width: w - 10 }} // -10 for gap
                                 onMouseEnter={() => setHoveredTask(task.id)}
                                 onMouseLeave={() => setHoveredTask(null)}
                               >
                                  {/* Signal Bar */}
                                  <div 
                                    className={`
                                      h-8 rounded relative overflow-hidden transition-all duration-300 border border-white/10
                                      ${task.status === 'blocked' ? 'bg-red-900/30 border-red-500/50' : ''}
                                      ${task.status === 'completed' ? 'bg-gray-800/50 grayscale opacity-60' : ''}
                                      ${task.status === 'active' || task.status === 'pending' ? `bg-opacity-20` : ''}
                                      ${isHovered ? 'scale-105 z-20 shadow-lg' : ''}
                                    `}
                                    style={{ 
                                       backgroundColor: task.status === 'blocked' ? undefined : `${cluster.color}33`, // 20% opacity hex
                                       borderColor: isHovered ? '#fff' : undefined,
                                       boxShadow: isHovered ? `0 0 15px ${cluster.color}` : undefined
                                    }}
                                  >
                                      {/* Neon Glow Line inside bar */}
                                      <div className={`absolute bottom-0 left-0 h-[2px] w-full`} style={{ backgroundColor: cluster.color }}></div>
                                      
                                      {/* Blocked Stripe Pattern */}
                                      {task.status === 'blocked' && (
                                        <div className="absolute inset-0 opacity-20" 
                                             style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, #ff0000 10px, #ff0000 20px)' }}>
                                        </div>
                                      )}

                                      {/* Content */}
                                      <div className="px-3 h-full flex items-center justify-between text-xs font-mono relative z-10">
                                         <span className="text-white font-bold truncate">{task.label}</span>
                                         {task.status === 'blocked' && <Lock size={12} className="text-red-400" />}
                                         {task.status === 'active' && <div className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />}
                                      </div>
                                  </div>
                               </div>
                             );
                          })}
                       </div>
                    </div>
                 ))}

                 {/* SVG Overlay for Connections */}
                 <svg className="absolute top-0 left-0 w-full h-full pointer-events-none z-0 overflow-visible">
                    <defs>
                      <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#555" />
                      </marker>
                      <marker id="arrowhead-red" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#ef4444" />
                      </marker>
                    </defs>
                    {TASKS.map(task => {
                       if (!task.dependencies.length) return null;
                       
                       // Find task coordinates
                       const taskY = getTaskY(task.id);
                       const taskX = getX(task.start); // Start of dependent task

                       return task.dependencies.map(depId => {
                          const depY = getTaskY(depId);
                          const depTask = TASKS.find(t => t.id === depId);
                          if (!depTask) return null;
                          const depX = getX(depTask.end); // End of source task

                          const isBlocked = task.status === 'blocked' && depId === 'u1'; // Mock blocked logic match
                          const color = isBlocked ? '#ef4444' : 'rgba(255, 255, 255, 0.2)';
                          const thickness = isBlocked ? 2 : 1;

                          // Curvy path
                          const path = `M ${depX} ${depY} C ${depX + 50} ${depY}, ${taskX - 50} ${taskY}, ${taskX} ${taskY}`;

                          return (
                             <g key={`${task.id}-${depId}`}>
                                <path 
                                  d={path} 
                                  fill="none" 
                                  stroke={color} 
                                  strokeWidth={thickness}
                                  strokeDasharray={isBlocked ? "5,5" : "none"}
                                  markerEnd={isBlocked ? "url(#arrowhead-red)" : "url(#arrowhead)"}
                                  className={isBlocked ? 'animate-pulse' : ''}
                                />
                                {isBlocked && (
                                   <circle cx={(depX + taskX)/2} cy={(depY + taskY)/2} r="10" fill="rgba(0,0,0,0.8)">
                                      <animate attributeName="r" values="10;12;10" dur="2s" repeatCount="indefinite" />
                                   </circle>
                                )}
                                {isBlocked && (
                                   <text x={(depX + taskX)/2} y={(depY + taskY)/2} dy="4" textAnchor="middle" fill="#ef4444" fontSize="10" fontWeight="bold">!</text>
                                )}
                             </g>
                          )
                       });
                    })}
                 </svg>

             </div>
         </div>
         
         {/* Footer Legend */}
         <div className="h-10 border-t border-white/10 bg-black/80 flex items-center px-4 gap-6 text-[10px] font-mono text-gray-500 uppercase">
             <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-cyan/20 border border-cyan/50"></div> Active
             </div>
             <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-red-900/30 border border-red-500/50 flex items-center justify-center">
                   <Lock size={8} className="text-red-500" />
                </div> Blocked
             </div>
             <div className="flex items-center gap-2">
                <div className="w-8 h-[2px] bg-red-500 border-dotted border-t-2 border-red-500"></div> Critical Path
             </div>
         </div>

      </div>
    </div>
  );
};

// Helper to find Y center of a task based on rendering order
function getTaskY(taskId: string): number {
  let y = 0;
  const HEADER_OFFSET = 0; // Relative to content area
  
  for (let i = 0; i < CLUSTERS.length; i++) {
     const cluster = CLUSTERS[i];
     const rowCenter = y + (80 / 2); // 80 is row height used in render
     
     if (cluster.id === TASKS.find(t => t.id === taskId)?.clusterId) {
        return rowCenter;
     }
     y += 80; // height of row + border
  }
  return 0;
}

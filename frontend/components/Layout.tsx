
import React, { useState } from 'react';
import { 
  Share2, 
  Search, 
  ArrowDownToLine, 
  GitBranch, 
  Menu, 
  ChevronLeft, 
  Cpu, 
  Layers,
  Workflow,
  Volume2,
  VolumeX,
  LayoutDashboard,
  CalendarClock,
  Lightbulb,
  ClipboardList,
  Settings,
  Map,
  FileText,
  // Architecture removed: lucide-react v0.554.0 does not export it.
  // Use LayoutDashboard icon as a substitute for the Architecture stage.
  Combine,
  Construction
} from 'lucide-react';
import { useSound } from './SoundManager';
import { ContextPrism, ContextItem } from './ContextPrism';
import { SysOpsTicker } from './SysOpsTicker';
import { NeuralLinkConfig } from './NeuralLinkConfig';

interface LayoutProps {
  children: React.ReactNode;
  currentModel?: string;
  vramUsage?: number; // percentage 0-100
  contextUsage?: { used: number; total: number; unit: string };
  systemStatus?: 'nominal' | 'warning' | 'critical' | 'warming_up';
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  // Footer Props
  logs?: string[];
  contextItems?: ContextItem[];
  onEjectContext?: (id: string) => void;
}

const LifecycleStage = ({
  icon,
  label,
  active,
  completed,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  completed: boolean;
}) => (
  <div className="flex flex-col items-center gap-1.5 text-center w-20">
    <div
      className={`
        relative w-8 h-8 flex items-center justify-center rounded-full border transition-all duration-300
        ${
          active
            ? 'bg-cyan/20 border-cyan shadow-[0_0_12px_rgba(0,240,255,0.7)]'
            : completed
            ? 'bg-green-500/20 border-green-500'
            : 'bg-white/5 border-white/10'
        }
      `}
    >
      {icon}
      {completed && !active && (
        <div className="absolute inset-0 bg-green-500/30 rounded-full animate-ping-slow"></div>
      )}
    </div>
    <span
      className={`text-[10px] font-mono uppercase tracking-wider transition-colors duration-300 ${
        active || completed ? 'text-white' : 'text-gray-500'
      }`}
    >
      {label}
    </span>
  </div>
);

const BlueprintLifecycle = ({ currentStage = 1 }: { currentStage: number }) => {
  const stages = [
    { icon: <Lightbulb size={14} />, label: 'Ideation' },
    { icon: <FileText size={14} />, label: 'Spec' },
    { icon: <LayoutDashboard size={14} />, label: 'Architecture' },
    { icon: <Construction size={14} />, label: 'Build' },
  ];

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex items-center">
        <div className="absolute w-full h-0.5 bg-white/10 top-1/2 -translate-y-1/2 left-0 right-0 transform -translate-y-3.5"></div>
        <div
          className="absolute h-0.5 bg-gradient-to-r from-cyan to-purple top-1/2 -translate-y-1/2 left-0 right-0 transform -translate-y-3.5 transition-all duration-500"
          style={{ width: `${((currentStage - 1) / (stages.length - 1)) * 100}%` }}
        ></div>
        <div className="flex justify-between w-full">
          {stages.map((stage, index) => (
            <LifecycleStage
              key={stage.label}
              icon={stage.icon}
              label={stage.label}
              active={index + 1 === currentStage}
              completed={index < currentStage}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export const Layout: React.FC<LayoutProps> = ({ 
  children,
  currentModel = 'Llama-3.3-70B',
  vramUsage = 45,
  contextUsage = { used: 32, total: 128, unit: 'k' },
  systemStatus = 'nominal',
  activeTab = 'dashboard',
  onTabChange,
  logs = [],
  contextItems = [],
  onEjectContext = () => {}
}) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [isDraftMode, setIsDraftMode] = useState(true);
  const { isEnabled, toggleSound, playClick } = useSound();

  // Calculate percentages for the header bar
  const contextPercent = (contextUsage.used / contextUsage.total) * 100;
  
  // Dynamic colors based on system status
  const vramColor = vramUsage > 80 ? 'text-amber' : 'text-cyan';
  const vramStroke = vramUsage > 80 ? '#ffbf00' : '#00f0ff';

  const handleNav = (tab: string) => {
    playClick();
    if (onTabChange) onTabChange(tab);
  };

  const handleToggleSound = () => {
    toggleSound();
    playClick();
  };

  const handleConfigOpen = () => {
    playClick();
    setIsConfigOpen(true);
  };

  const isWarmingUp = systemStatus === 'warming_up';
  const statusDotClasses = (() => {
    switch (systemStatus) {
      case 'warning':
        return 'bg-amber shadow-amber';
      case 'critical':
        return 'bg-red-500 shadow-red-500';
      case 'warming_up':
        return 'bg-amber/90 shadow-[0_0_12px_rgba(250,204,21,0.7)]';
      default:
        return 'bg-green-500 shadow-green-500';
    }
  })();

  return (
    <div className="flex h-screen w-full bg-void text-white font-sans overflow-hidden selection:bg-cyan selection:text-black">
      {/* Global Background Effects */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `linear-gradient(rgba(0, 240, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 240, 255, 0.05) 1px, transparent 1px)`,
            backgroundSize: '40px 40px'
          }}
        ></div>
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-purple/10 blur-[120px] rounded-full mix-blend-screen animate-pulse-fast"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cyan/5 blur-[120px] rounded-full mix-blend-screen"></div>
      </div>

      {/* Sidebar */}
      <aside 
        className={`relative z-30 flex flex-col border-r border-white/10 bg-panel/50 backdrop-blur-xl transition-all duration-300 ease-out ${isSidebarCollapsed ? 'w-16' : 'w-64'}`}
      >
        <div className="h-16 flex items-center justify-center border-b border-white/10 shrink-0">
          <button 
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            className="p-2 text-cyan hover:bg-white/5 rounded-md transition-colors focus:outline-none"
            aria-label="Toggle Sidebar"
          >
             {isSidebarCollapsed ? (
               <Menu size={20} />
             ) : (
               <div className="flex items-center gap-3">
                 <ChevronLeft size={20} />
                 <span className="font-mono font-bold text-sm tracking-widest text-white">NEXUS</span>
               </div>
             )}
          </button>
        </div>

        <nav className="flex-1 py-6 space-y-2 overflow-y-auto overflow-x-hidden scrollbar-hide">
           <SidebarItem 
             icon={<LayoutDashboard size={20} />} 
             label="Mission Control" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'mission_control'}
             onClick={() => handleNav('mission_control')}
           />
           <SidebarItem 
             icon={<CalendarClock size={20} />} 
             label="Dependency Map" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'timeline'}
             onClick={() => handleNav('timeline')}
           />
           <SidebarItem 
             icon={<Map size={20} />} 
             label="Project Roadmap" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'roadmap'}
             onClick={() => handleNav('roadmap')}
           />
           <SidebarItem 
             icon={<Lightbulb size={20} />} 
             label="Strategy Node" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'strategy'}
             onClick={() => handleNav('strategy')}
           />
           <SidebarItem 
             icon={<ClipboardList size={20} />} 
             label="Backlog Refinement" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'pm_dissection'}
             onClick={() => handleNav('pm_dissection')}
           />
           <SidebarItem 
             icon={<Share2 size={20} />} 
             label="Nexus Graph" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'nexus'}
             onClick={() => handleNav('nexus')}
           />
           <SidebarItem 
             icon={<Search size={20} />} 
             label="Deep Research" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'research'}
             onClick={() => handleNav('research')}
           />
           <SidebarItem 
             icon={<Workflow size={20} />} 
             label="Construct Flow" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'workflow'}
             onClick={() => handleNav('workflow')}
           />
           <SidebarItem 
             icon={<ArrowDownToLine size={20} />} 
             label="Ingest Pipeline" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'ingest'}
             onClick={() => handleNav('ingest')}
           />
           <SidebarItem 
             icon={<GitBranch size={20} />} 
             label="Repo Manager" 
             collapsed={isSidebarCollapsed} 
             active={activeTab === 'repo'}
             onClick={() => handleNav('repo')}
           />
        </nav>

        <div className="p-4 border-t border-white/10 shrink-0 space-y-4">
           <div 
             onClick={handleToggleSound}
             className={`flex items-center gap-3 cursor-pointer group ${isSidebarCollapsed ? 'justify-center' : ''}`}
           >
             <div className={`p-1.5 rounded transition-colors ${isEnabled ? 'text-cyan bg-cyan/10' : 'text-gray-500 hover:text-gray-300'}`}>
                {isEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
             </div>
             {!isSidebarCollapsed && (
               <span className="font-mono text-xs text-gray-500 group-hover:text-cyan transition-colors">AUDIO_FX</span>
             )}
           </div>

           <div className={`flex items-center gap-3 ${isSidebarCollapsed ? 'justify-center' : ''}`}>
              <div
                className={`w-2 h-2 rounded-full transition-colors duration-300 ${statusDotClasses}`}
              ></div>
              {!isSidebarCollapsed && (
                isWarmingUp ? (
                  <span className="rounded-full border border-amber/60 bg-amber/10 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-amber">
                    WARMING UP
                  </span>
                ) : (
                  <span className="font-mono text-xs text-gray-400">SYS_ONLINE</span>
                )
              )}
           </div>
        </div>
      </aside>

      {/* Main Column */}
      <div className="flex flex-col flex-1 relative z-20 h-full min-w-0">
        
        {/* HUD Header */}
        <header className="h-16 border-b border-white/10 bg-panel/30 backdrop-blur-md flex items-center justify-between px-6 shrink-0 relative z-40">
           <div className="flex items-center gap-6 min-w-0">
              <h1 className="hidden md:block text-xl font-bold font-mono tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan to-purple whitespace-nowrap">
                ARGOS_NEXUS<span className="text-white text-sm ml-1">JR</span>
              </h1>
              <div className="hidden md:block h-6 w-[1px] bg-white/10"></div>
              <div className="flex items-center gap-3 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 hover:border-purple/50 transition-colors cursor-help group">
                 <Layers size={14} className="text-purple group-hover:animate-pulse" />
                 <span className="font-mono text-xs text-gray-300 group-hover:text-white transition-colors">{currentModel}</span>
              </div>
           </div>

           <div className="flex items-center gap-6 md:gap-8 ml-auto">
              {/* Draft Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className={`font-mono text-xs uppercase ${isDraftMode ? 'text-cyan' : 'text-gray-500'}`}>
                  {isDraftMode ? 'Draft Mode' : 'Ops Mode'}
                </span>
                <button
                  onClick={() => setIsDraftMode(!isDraftMode)}
                  className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors ${
                    isDraftMode ? 'bg-cyan/30' : 'bg-white/10'
                  }`}
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      isDraftMode ? 'translate-x-5 bg-cyan' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {isDraftMode ? (
                <BlueprintLifecycle currentStage={2} />
              ) : (
                <>
                  <div className="flex flex-col gap-1.5 w-32 md:w-48">
                     <div className="flex justify-between text-[10px] font-mono uppercase text-gray-400">
                        <span className="tracking-wider">Ctx Window</span>
                        <span>{contextUsage.used}{contextUsage.unit}</span>
                     </div>
                     <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
                        <div 
                          className="h-full bg-gradient-to-r from-cyan to-blue-600 shadow-neon-cyan relative" 
                          style={{ width: `${contextPercent}%` }}
                        >
                          <div className="absolute right-0 top-0 bottom-0 w-[2px] bg-white mix-blend-overlay"></div>
                        </div>
                     </div>
                  </div>

                  <div className="flex items-center gap-4 pl-6 border-l border-white/10">
                     <div className="relative w-10 h-10 flex items-center justify-center">
                        <svg className="w-full h-full transform -rotate-90">
                           <circle cx="20" cy="20" r="16" stroke="currentColor" strokeWidth="3" fill="transparent" className="text-white/5" />
                           <circle 
                              cx="20" cy="20" r="16" 
                              stroke={vramStroke}
                              strokeWidth="3" 
                              fill="transparent" 
                              strokeDasharray={100} 
                              strokeDashoffset={100 - vramUsage} 
                              className="transition-all duration-700 ease-out"
                              strokeLinecap="round"
                           />
                        </svg>
                        <Cpu size={14} className="absolute text-gray-500" />
                     </div>
                     <div className="hidden lg:flex flex-col">
                        <span className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Shared Mem</span>
                        <span className={`text-sm font-bold font-mono ${vramColor}`}>{vramUsage}%</span>
                     </div>
                  </div>
                </>
              )}
              {/* Settings Trigger */}
              <button 
                onClick={handleConfigOpen}
                className="p-2 text-gray-400 hover:text-cyan hover:bg-cyan/10 rounded-lg transition-colors border border-transparent hover:border-cyan/30 group"
                title="Neural Link Config"
              >
                <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
              </button>
           </div>
        </header>

        {/* Main Viewport Content - Adjusted padding bottom to clear footer */}
        <main className="flex-1 relative overflow-hidden bg-black/40">
           {/* Subtle Scanline Overlay */}
           <div className="absolute inset-0 pointer-events-none z-50 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_3px,3px_100%] opacity-30"></div>
           
           <div className="absolute inset-0 overflow-y-auto overflow-x-hidden p-0 md:p-4 pb-24 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
             <div className="max-w-[1920px] mx-auto min-h-full">
                {children}
             </div>
           </div>
        </main>

        {/* Global Footer Elements */}
        <div className="absolute bottom-0 left-0 right-0 z-50 flex flex-col">
           {contextItems.length > 0 && (
              <ContextPrism items={contextItems} totalCapacity={128000} onEject={onEjectContext} />
           )}
           <SysOpsTicker logs={logs} />
        </div>
      </div>

      {/* Global Modals */}
      <NeuralLinkConfig isOpen={isConfigOpen} onClose={() => setIsConfigOpen(false)} />
    </div>
  );
};

const SidebarItem = ({ 
  icon, 
  label, 
  collapsed, 
  active,
  onClick
}: { 
  icon: React.ReactNode, 
  label: string, 
  collapsed: boolean, 
  active?: boolean,
  onClick?: () => void
}) => (
  <div 
    onClick={onClick}
    className={`
    group flex items-center gap-4 px-4 py-3 cursor-pointer transition-all duration-200 
    border-l-2 relative overflow-hidden
    ${active 
      ? 'border-cyan bg-cyan/5 text-cyan' 
      : 'border-transparent text-gray-500 hover:text-white hover:bg-white/5 hover:border-white/20'}
  `}>
    <div className={`relative z-10 transition-transform duration-300 ${active ? 'scale-110 drop-shadow-[0_0_8px_rgba(0,240,255,0.5)]' : 'group-hover:scale-110'}`}>
      {icon}
    </div>
    {!collapsed && (
      <span className={`font-mono text-xs font-medium tracking-widest uppercase whitespace-nowrap relative z-10 ${active ? 'text-cyan' : ''}`}>
        {label}
      </span>
    )}
    {active && <div className="absolute inset-0 bg-gradient-to-r from-cyan/10 to-transparent w-1/2"></div>}
  </div>
);

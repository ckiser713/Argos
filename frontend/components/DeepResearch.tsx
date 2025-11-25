import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Bot, 
  User, 
  FileText, 
  Code, 
  Search, 
  Database, 
  Loader2, 
  ChevronRight, 
  ChevronDown,
  Maximize2,
  Minimize2,
  Globe,
  Share2,
  Terminal as TerminalIcon
} from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';
import { TerminalText } from './TerminalText';

// --- Types ---
interface LogStep {
  id: string;
  label: string;
  status: 'pending' | 'processing' | 'complete';
  detail?: string;
}

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string; // The final answer or user query
  logs?: LogStep[]; // For agent only: the "thinking" process
  timestamp: string;
  relatedDocId?: string; // If this message references a specific doc
  highlightIds?: string[]; // IDs of paragraphs to highlight in the doc
}

interface Doc {
  id: string;
  title: string;
  type: 'pdf' | 'code';
  content: React.ReactNode; // storing pre-parsed JSX for the demo
}

// --- Mock Data ---

const MOCK_DOCS: Doc[] = [
  {
    id: 'doc_alpha',
    title: 'Project_Titan_Specs.pdf',
    type: 'pdf',
    content: (
      <div className="space-y-4 font-serif text-gray-300 leading-relaxed">
        <h1 className="text-2xl font-bold text-white font-sans mb-4">Project Titan: Neural Interface Protocols</h1>
        <p className="text-xs text-gray-500 font-mono mb-6">CONFIDENTIAL // CLEARANCE LEVEL 4</p>
        
        <div id="para-1" className="p-2 transition-all duration-500 rounded">
          <h3 className="text-lg font-bold text-white font-sans mb-2">1.0 Executive Summary</h3>
          <p>The Titan initiative aims to bridge the gap between biological synapses and silicon-based logic gates. Early trials indicate a <span className="text-cyan font-mono">340% increase</span> in throughput when using the direct-link adapters.</p>
        </div>

        <div id="para-2" className="p-2 transition-all duration-500 rounded">
          <h3 className="text-lg font-bold text-white font-sans mb-2">2.1 Thermal Throttling</h3>
          <p>During heavy inference loads (batch size &gt; 512), the VRAM junction temperature exceeded safe operating limits (95°C). It is recommended to implement active liquid cooling loops for all edge nodes deployed in Sector 7.</p>
        </div>

        <div id="para-3" className="p-2 transition-all duration-500 rounded">
          <h3 className="text-lg font-bold text-white font-sans mb-2">3.0 Latency Optimization</h3>
          <p>Network round-trip time has been reduced to 12ms by utilizing the new sub-space transmission protocol. This allows for near real-time haptic feedback in the operator's rig.</p>
        </div>
      </div>
    )
  },
  {
    id: 'doc_beta',
    title: 'ingress_controller.rs',
    type: 'code',
    content: (
      <div className="font-mono text-sm space-y-1 text-gray-400">
         <div className="text-gray-500">// Core ingress logic for the neural bus</div>
         <div><span className="text-purple">fn</span> <span className="text-cyan">handle_stream</span>(stream: TcpStream) &#123;</div>
         <div id="code-1" className="pl-4 p-1 rounded transition-all duration-500">
             <span className="text-purple">let</span> mut buffer = [<span className="text-amber">0</span>; <span className="text-amber">1024</span>];
             <span className="text-gray-500">// Buffer allocation crucial for memory safety</span>
         </div>
         <div id="code-2" className="pl-4 p-1 rounded transition-all duration-500">
             stream.<span className="text-cyan">read</span>(&mut buffer).<span className="text-cyan">unwrap</span>();
             <span className="text-purple">if</span> buffer[<span className="text-amber">0</span>] == <span className="text-amber">0xDEAD</span> &#123;
                 <span className="text-cyan">panic!</span>(<span className="text-green-400">"Neural overload detected!"</span>);
             &#125;
         </div>
         <div>&#125;</div>
      </div>
    )
  }
];

// Helper Component for Tool Badges
const ToolBadge = ({ icon, label, active }: { icon: React.ReactNode, label: string, active: boolean }) => (
  <div className={`
    flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono transition-all duration-300 border
    ${active 
      ? 'bg-white/10 text-white border-white/20 shadow-[0_0_10px_rgba(255,255,255,0.2)]' 
      : 'bg-transparent text-gray-600 border-transparent'}
  `}>
    <span className={active ? 'text-cyan' : ''}>{icon}</span>
    <span>{label}</span>
  </div>
);

export const DeepResearch: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg_0',
      role: 'agent',
      content: 'Deep Research Agent v9.2 online. Connected to local Knowledge Graph. What topic shall we investigate today?',
      timestamp: '09:41',
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Neural Config State
  const [currentModel, setCurrentModel] = useState('Deep Reader (Qwen 1M)');
  const [agentState, setAgentState] = useState<'idle' | 'planning' | 'generating'>('idle');
  const [activeTools, setActiveTools] = useState<string[]>([]);

  const [activeDocId, setActiveDocId] = useState<string>('doc_alpha');
  const [activeHighlights, setActiveHighlights] = useState<string[]>([]);
  const [splitRatio, setSplitRatio] = useState(50); // percentage

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const resizeRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle Resize Logic
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const newWidth = (e.clientX / window.innerWidth) * 100;
      if (newWidth > 20 && newWidth < 80) {
        setSplitRatio(newWidth);
      }
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
    };

    const handleMouseDown = (e: React.MouseEvent) => {
      e.preventDefault();
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
    };

    const resizer = resizeRef.current;
    if (resizer) {
      resizer.addEventListener('mousedown', handleMouseDown as any);
    }

    return () => {
      if (resizer) {
        resizer.removeEventListener('mousedown', handleMouseDown as any);
      }
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsProcessing(true);

    // Simulate Agent Thinking Process
    simulateAgentResponse();
  };

  const simulateAgentResponse = () => {
    // Initial State: Planning
    setAgentState('planning');
    setActiveTools([]);

    // Create placeholder message
    const msgId = (Date.now() + 1).toString();
    const initialLog: LogStep[] = [
      { id: 'l1', label: 'Parsing Query Intent', status: 'processing' },
    ];
    
    setMessages(prev => [...prev, {
      id: msgId,
      role: 'agent',
      content: '', // Empty initially
      logs: initialLog,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    // Step 1: Finish Parsing, Start Graph Search
    setTimeout(() => {
      updateLog(msgId, 'l1', 'complete');
      addLog(msgId, { id: 'l2', label: 'Traversing Knowledge Graph', status: 'processing', detail: 'Searching for "Thermal Throttling"' });
      setActiveTools(prev => [...prev, 'graph']); // Activate Graph Tool
    }, 1000);

    // Step 2: Finish Graph, Start Reading
    setTimeout(() => {
      updateLog(msgId, 'l2', 'complete');
      addLog(msgId, { id: 'l3', label: 'Reading Documents', status: 'processing', detail: 'Scanning Project_Titan_Specs.pdf...' });
      // Remove graph tool, add web/repl if needed, here we just show deep read implied
      setActiveTools(['graph']); // Keep graph active as context
    }, 2500);
    
    // Highlight trigger during "Reading"
    setTimeout(() => {
        setActiveDocId('doc_alpha');
        setActiveHighlights(['para-2']); // Highlight thermal throttling section
    }, 2600);

    // Step 3: Finish Reading, Start Generating Answer
    setTimeout(() => {
        updateLog(msgId, 'l3', 'complete');
        setAgentState('generating'); // Switch color to green
        setActiveTools([]); // Tools done
        
        // Finalize message
        setMessages(prev => prev.map(m => {
            if (m.id === msgId) {
                return {
                    ...m,
                    content: "According to the Titan Specs (Section 2.1), there is a significant thermal throttling issue when batch size exceeds 512. The junction temperature hits 95°C, necessitating active liquid cooling for Sector 7 deployments.",
                    relatedDocId: 'doc_alpha',
                    highlightIds: ['para-2']
                };
            }
            return m;
        }));
        setIsProcessing(false);
    }, 4500);

    // Step 4: Back to Idle
    setTimeout(() => {
        setAgentState('idle');
    }, 5000);
  };

  const updateLog = (msgId: string, logId: string, status: 'complete') => {
    setMessages(prev => prev.map(m => {
        if (m.id === msgId && m.logs) {
            return {
                ...m,
                logs: m.logs.map(l => l.id === logId ? { ...l, status } : l)
            };
        }
        return m;
    }));
  };

  const addLog = (msgId: string, log: LogStep) => {
    setMessages(prev => prev.map(m => {
        if (m.id === msgId && m.logs) {
            return { ...m, logs: [...m.logs, log] };
        }
        return m;
    }));
  };

  // Visual helpers for Agent State
  const getAgentVisuals = () => {
    switch (agentState) {
      case 'planning': return { color: 'text-purple', bg: 'bg-purple', shadow: 'shadow-neon-purple' };
      case 'generating': return { color: 'text-green-500', bg: 'bg-green-500', shadow: 'shadow-green-500' };
      default: return { color: 'text-cyan', bg: 'bg-cyan', shadow: 'shadow-neon-cyan' };
    }
  };
  const visual = getAgentVisuals();

  return (
    <div className="flex h-[calc(100vh-140px)] w-full overflow-hidden animate-fade-in relative rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm">
      
      {/* LEFT PANEL: Interaction */}
      <div style={{ width: `${splitRatio}%` }} className="flex flex-col min-w-[350px] relative transition-width duration-100 ease-linear">
         
         {/* NEURAL CONFIG TOOLBAR */}
         <div className="h-14 border-b border-white/10 flex items-center justify-between px-4 bg-white/5 backdrop-blur-md relative z-20">
            {/* Left: Model Selector */}
            <div className="flex items-center gap-3">
               <Bot size={18} className={`${visual.color} transition-colors duration-500`} />
               <div className="relative group">
                   <select 
                     value={currentModel} 
                     onChange={e => setCurrentModel(e.target.value)}
                     className="bg-transparent text-[11px] font-mono font-bold text-white appearance-none focus:outline-none cursor-pointer pr-4 uppercase tracking-wider hover:text-cyan transition-colors"
                   >
                       <option className="bg-void text-gray-300">Deep Reader (Qwen 1M)</option>
                       <option className="bg-void text-gray-300">Code Expert (Qwen Coder)</option>
                   </select>
                   <ChevronDown size={12} className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500" />
               </div>
            </div>

            {/* Center: Tool Indicators */}
            <div className="flex items-center gap-2">
                <ToolBadge 
                  icon={<TerminalIcon size={12}/>} 
                  label="REPL" 
                  active={activeTools.includes('repl')} 
                />
                <ToolBadge 
                  icon={<Globe size={12}/>} 
                  label="WEB" 
                  active={activeTools.includes('web')} 
                />
                <ToolBadge 
                  icon={<Share2 size={12}/>} 
                  label="GRAPH" 
                  active={activeTools.includes('graph')} 
                />
            </div>

            {/* Right: Agent State Pulse */}
            <div className="flex items-center gap-3">
                <span className={`text-[10px] font-mono uppercase tracking-widest hidden sm:block ${visual.color}`}>
                   {agentState}
                </span>
                <div className="relative flex h-3 w-3">
                   <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${visual.bg}`}></span>
                   <span className={`relative inline-flex rounded-full h-3 w-3 ${visual.bg} ${visual.shadow}`}></span>
                </div>
            </div>
         </div>

         {/* Chat Area */}
         <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                 
                 {/* Avatar */}
                 <div className={`
                    w-8 h-8 rounded shrink-0 flex items-center justify-center border transition-all duration-300
                    ${msg.role === 'agent' 
                      ? `bg-cyan/10 border-cyan/30 text-cyan` 
                      : 'bg-purple/10 border-purple/30 text-purple'}
                 `}>
                    {msg.role === 'agent' ? <Bot size={16} /> : <User size={16} />}
                 </div>

                 {/* Message Bubble */}
                 <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className="flex items-center gap-2 mb-1">
                       <span className="text-[10px] font-mono text-gray-500">{msg.timestamp}</span>
                       <span className="text-[10px] font-mono text-gray-600 uppercase">{msg.role}</span>
                    </div>

                    {/* Agent Thinking Logs */}
                    {msg.logs && msg.logs.length > 0 && (
                        <div className="mb-3 w-full bg-black/40 rounded border border-white/5 p-2 space-y-2 font-mono text-xs">
                            {msg.logs.map(log => (
                                <div key={log.id} className="flex items-center gap-2">
                                    {log.status === 'processing' ? (
                                        <Loader2 size={10} className="text-amber animate-spin" />
                                    ) : log.status === 'complete' ? (
                                        <div className="w-2.5 h-2.5 rounded-full border border-cyan flex items-center justify-center">
                                            <div className="w-1 h-1 bg-cyan rounded-full"></div>
                                        </div>
                                    ) : (
                                        <div className="w-2.5 h-2.5 rounded-full border border-gray-600"></div>
                                    )}
                                    <span className={`${log.status === 'processing' ? 'text-amber' : log.status === 'complete' ? 'text-gray-400 line-through opacity-60' : 'text-gray-500'}`}>
                                        {log.label}
                                    </span>
                                    {log.detail && log.status !== 'pending' && (
                                        <span className="text-gray-600 ml-auto hidden sm:block truncate max-w-[150px]">{log.detail}</span>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Actual Text Content */}
                    {msg.content && (
                       <div className={`
                          p-3 rounded-lg text-sm leading-relaxed border shadow-lg
                          ${msg.role === 'user' 
                             ? 'bg-purple/10 border-purple/20 text-gray-200 rounded-tr-none' 
                             : 'bg-cyan/5 border-cyan/10 text-gray-100 rounded-tl-none'}
                       `}>
                          <TerminalText text={msg.content} speed={10} />
                          
                          {/* Citation Link */}
                          {msg.relatedDocId && (
                             <button 
                               onClick={() => {
                                   setActiveDocId(msg.relatedDocId!);
                                   if (msg.highlightIds) setActiveHighlights(msg.highlightIds);
                               }}
                               className="mt-3 flex items-center gap-2 text-xs font-mono text-cyan hover:text-white hover:underline transition-colors w-full p-2 bg-cyan/5 rounded border border-cyan/10"
                             >
                                <Search size={12} />
                                <span>SOURCE: {MOCK_DOCS.find(d => d.id === msg.relatedDocId)?.title}</span>
                             </button>
                          )}
                       </div>
                    )}
                 </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
         </div>

         {/* Input Area */}
         <div className="p-4 border-t border-white/10 bg-panel/50 backdrop-blur-md">
            <div className="relative group">
                <input 
                  type="text" 
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Enter command or query..."
                  disabled={isProcessing}
                  className="w-full bg-black/50 border border-white/20 rounded px-4 py-3 pr-12 text-sm font-mono text-white focus:outline-none focus:border-cyan/50 focus:shadow-[0_0_15px_rgba(0,240,255,0.1)] transition-all placeholder:text-gray-600 disabled:opacity-50"
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={!inputValue || isProcessing}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-cyan hover:bg-cyan/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                >
                    <Send size={16} />
                </button>
            </div>
         </div>
      </div>

      {/* DRAGGER HANDLE */}
      <div 
         ref={resizeRef}
         className="w-1 hover:w-1.5 bg-white/5 hover:bg-cyan/50 cursor-col-resize flex items-center justify-center transition-all z-20 group"
      >
          <div className="h-8 w-full bg-gray-600 group-hover:bg-cyan rounded-full mx-[1px]"></div>
      </div>

      {/* RIGHT PANEL: Context Deck */}
      <div className="flex-1 flex flex-col min-w-[300px] bg-panel/30 backdrop-blur-xl border-l border-white/5">
          
          {/* Tabs */}
          <div className="flex items-center overflow-x-auto border-b border-white/10 scrollbar-hide bg-black/20">
             <div className="px-4 py-3 text-xs font-mono font-bold text-gray-500 uppercase tracking-widest shrink-0 border-r border-white/5">
                CONTEXT_DECK
             </div>
             {MOCK_DOCS.map(doc => (
                <button
                  key={doc.id}
                  onClick={() => {
                      setActiveDocId(doc.id);
                      // Clear highlights when manually switching unless we want to persist
                  }}
                  className={`
                    flex items-center gap-2 px-4 py-3 text-xs font-mono border-r border-white/5 transition-colors whitespace-nowrap
                    ${activeDocId === doc.id ? 'bg-white/5 text-cyan border-b-2 border-b-cyan' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'}
                  `}
                >
                  {doc.type === 'pdf' ? <FileText size={14} /> : <Code size={14} />}
                  {doc.title}
                </button>
             ))}
          </div>

          {/* Doc Content */}
          <div className="flex-1 overflow-y-auto p-8 relative">
              {/* Background Noise for document feel */}
              <div className="absolute inset-0 opacity-[0.03] bg-[url('https://www.transparenttextures.com/patterns/graphy.png')] pointer-events-none"></div>

              {MOCK_DOCS.map(doc => {
                  if (doc.id !== activeDocId) return null;

                  return (
                    <div key={doc.id} className="max-w-3xl mx-auto animate-fade-in relative z-10">
                        {/* Recursive clone to inject highlight styles into the mock content */}
                        {React.Children.map(doc.content, (child: any) => {
                            if (!React.isValidElement(child)) return child;
                            
                            // Simple approach: clone the wrapper div and add logic to its children if needed.
                            // Since MOCK_DOCS content is structured as div > div(id), we iterate children.
                            
                            if (child.props.children) {
                                const enhancedChildren = React.Children.map(child.props.children, (grandChild: any) => {
                                    if (React.isValidElement(grandChild) && grandChild.props.id) {
                                        const isHighlighted = activeHighlights.includes(grandChild.props.id);
                                        return React.cloneElement(grandChild as React.ReactElement<any>, {
                                            className: `
                                                ${grandChild.props.className} 
                                                ${isHighlighted ? 'bg-amber/10 border-l-2 border-amber shadow-[0_0_15px_rgba(255,191,0,0.1)]' : 'border-l-2 border-transparent'}
                                            `
                                        });
                                    }
                                    return grandChild;
                                });
                                return React.cloneElement(child, {}, enhancedChildren);
                            }
                            return child;
                        })}
                    </div>
                  );
              })}
          </div>

          {/* Context Footer Status */}
          <div className="h-8 border-t border-white/10 bg-black/40 flex items-center px-4 justify-between text-[10px] font-mono text-gray-500">
              <div className="flex items-center gap-2">
                 <Database size={12} />
                 <span>TOKENS: 14,204 / 128,000</span>
              </div>
              <div className="flex items-center gap-2">
                 <span>READ_MODE: ACTIVE</span>
              </div>
          </div>
      </div>

    </div>
  );
};

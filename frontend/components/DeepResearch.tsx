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
  ChevronDown,
  Globe,
  Share2,
  Terminal as TerminalIcon
} from 'lucide-react';
import { GlassCard } from './GlassCard';
import { TerminalText } from './TerminalText';
import { useAgentRuns, useCreateAgentRun } from '../src/hooks/useAgentRuns';
import { AgentRun } from '../src/domain/types';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: string;
  logs?: any[];
}

const ToolBadge = ({ icon, label, active }: { icon: React.ReactNode, label: string, active: boolean }) => (
  <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono transition-all duration-300 border ${active ? 'bg-white/10 text-white border-white/20 shadow-[0_0_10px_rgba(255,255,255,0.2)]' : 'bg-transparent text-gray-600 border-transparent'}`}>
    <span className={active ? 'text-cyan' : ''}>{icon}</span>
    <span>{label}</span>
  </div>
);

export const DeepResearch: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);

  const projectId = "default_project";
  const { data: runsData, isLoading: isLoadingRuns } = useAgentRuns(projectId);
  
  const createRun = useCreateAgentRun(projectId, {
    onSuccess: (data) => {
      setCurrentRunId(data.id);
      setLogs([]);
    },
  });

  useEffect(() => {
    if (currentRunId) {
      const eventSource = new EventSource(`/api/agents/runs/${currentRunId}/stream`);
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, data]);
        if (data.event === 'on_chain_end') {
            eventSource.close();
            setCurrentRunId(null);
        }
      };
      return () => {
        eventSource.close();
      };
    }
  }, [currentRunId]);
  
  const isProcessing = createRun.isPending || currentRunId !== null;

  const messages: Message[] = (runsData?.items || []).flatMap(run => {
    const msgs: Message[] = [];
    msgs.push({
        id: `${run.id}-input`,
        role: 'user',
        content: run.input_prompt,
        timestamp: new Date(run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    });
    if (run.output_summary) {
        msgs.push({
            id: `${run.id}-output`,
            role: 'agent',
            content: run.output_summary,
            timestamp: new Date(run.finished_at || run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
    }
    return msgs;
  }).sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const [currentModel, setCurrentModel] = useState('Deep Reader (Qwen 1M)');
  const [splitRatio, setSplitRatio] = useState(50);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const resizeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, logs]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const newWidth = (e.clientX / window.innerWidth) * 100;
      if (newWidth > 20 && newWidth < 80) setSplitRatio(newWidth);
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
    if (resizer) resizer.addEventListener('mousedown', handleMouseDown as any);
    return () => {
      if (resizer) resizer.removeEventListener('mousedown', handleMouseDown as any);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    createRun.mutate({ project_id: projectId, agent_id: "researcher", input_prompt: inputValue });
    setInputValue('');
  };

  const visual = isProcessing ? { color: 'text-purple', bg: 'bg-purple', shadow: 'shadow-neon-purple' } : { color: 'text-cyan', bg: 'bg-cyan', shadow: 'shadow-neon-cyan' };

  return (
    <div className="flex h-[calc(100vh-140px)] w-full overflow-hidden animate-fade-in relative rounded-xl border border-white/10 bg-black/40 backdrop-blur-sm">
      <div style={{ width: `${splitRatio}%` }} className="flex flex-col min-w-[350px] relative transition-width duration-100 ease-linear">
         <div className="h-14 border-b border-white/10 flex items-center justify-between px-4 bg-white/5 backdrop-blur-md relative z-20">
            <div className="flex items-center gap-3">
               <Bot size={18} className={`${visual.color} transition-colors duration-500`} />
               <div className="relative group">
                   <select value={currentModel} onChange={e => setCurrentModel(e.target.value)} className="bg-transparent text-[11px] font-mono font-bold text-white appearance-none focus:outline-none cursor-pointer pr-4 uppercase tracking-wider hover:text-cyan transition-colors">
                       <option className="bg-void text-gray-300">Deep Reader (Qwen 1M)</option>
                       <option className="bg-void text-gray-300">Code Expert (Qwen Coder)</option>
                   </select>
                   <ChevronDown size={12} className="absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500" />
               </div>
            </div>
            <div className="flex items-center gap-2">
                <ToolBadge icon={<TerminalIcon size={12}/>} label="REPL" active={false} />
                <ToolBadge icon={<Globe size={12}/>} label="WEB" active={false} />
                <ToolBadge icon={<Share2 size={12}/>} label="GRAPH" active={isProcessing} />
            </div>
            <div className="flex items-center gap-3">
                <span className={`text-[10px] font-mono uppercase tracking-widest hidden sm:block ${visual.color}`}>{isProcessing ? 'Processing' : 'Idle'}</span>
                <div className="relative flex h-3 w-3">
                   {isProcessing && <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${visual.bg}`}></span>}
                   <span className={`relative inline-flex rounded-full h-3 w-3 ${visual.bg} ${visual.shadow}`}></span>
                </div>
            </div>
         </div>
         <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
            {isLoadingRuns && <div>Loading agent runs...</div>}
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                 <div className={`w-8 h-8 rounded shrink-0 flex items-center justify-center border transition-all duration-300 ${msg.role === 'agent' ? `bg-cyan/10 border-cyan/30 text-cyan` : 'bg-purple/10 border-purple/30 text-purple'}`}>
                    {msg.role === 'agent' ? <Bot size={16} /> : <User size={16} />}
                 </div>
                 <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className="flex items-center gap-2 mb-1">
                       <span className="text-[10px] font-mono text-gray-500">{msg.timestamp}</span>
                       <span className="text-[10px] font-mono text-gray-600 uppercase">{msg.role}</span>
                    </div>
                    {currentRunId && msg.id.startsWith(currentRunId) && logs.length > 0 && (
                        <div className="mb-3 w-full bg-black/40 rounded border border-white/5 p-2 space-y-2 font-mono text-xs">
                            {logs.map((log, i) => (
                                <div key={i} className="flex items-center gap-2">
                                    <Loader2 size={10} className="text-amber animate-spin" />
                                    <span className="text-amber">{log.event}</span>
                                    <span className="text-gray-600 ml-auto hidden sm:block truncate max-w-[150px]">{log.name}</span>
                                </div>
                            ))}
                        </div>
                    )}
                    {msg.content && (
                       <div className={`p-3 rounded-lg text-sm leading-relaxed border shadow-lg ${msg.role === 'user' ? 'bg-purple/10 border-purple/20 text-gray-200 rounded-tr-none' : 'bg-cyan/5 border-cyan/10 text-gray-100 rounded-tl-none'}`}>
                          <TerminalText text={msg.content} speed={10} />
                       </div>
                    )}
                 </div>
              </div>
            ))}
            {isProcessing && currentRunId && (
                <div className="flex gap-4">
                    <div className="w-8 h-8 rounded shrink-0 flex items-center justify-center border bg-cyan/10 border-cyan/30 text-cyan"><Bot size={16} /></div>
                    <div className="flex flex-col max-w-[85%] items-start">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-mono text-gray-500">...</span>
                            <span className="text-[10px] font-mono text-gray-600 uppercase">agent</span>
                        </div>
                        <div className="p-3 rounded-lg text-sm leading-relaxed border shadow-lg bg-cyan/5 border-cyan/10 text-gray-100 rounded-tl-none">
                            <Loader2 size={16} className="animate-spin" />
                        </div>
                    </div>
                </div>
            )}
            <div ref={messagesEndRef} />
         </div>
         <div className="p-4 border-t border-white/10 bg-panel/50 backdrop-blur-md">
            <div className="relative group">
                <input type="text" value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()} placeholder="Enter command or query..." disabled={isProcessing} className="w-full bg-black/50 border border-white/20 rounded px-4 py-3 pr-12 text-sm font-mono text-white focus:outline-none focus:border-cyan/50 focus:shadow-[0_0_15px_rgba(0,240,255,0.1)] transition-all placeholder:text-gray-600 disabled:opacity-50" />
                <button onClick={handleSendMessage} disabled={!inputValue || isProcessing} className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-cyan hover:bg-cyan/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"><Send size={16} /></button>
            </div>
         </div>
      </div>
      <div ref={resizeRef} className="w-1 hover:w-1.5 bg-white/5 hover:bg-cyan/50 cursor-col-resize flex items-center justify-center transition-all z-20 group"><div className="h-8 w-full bg-gray-600 group-hover:bg-cyan rounded-full mx-[1px]"></div></div>
      <div className="flex-1 flex flex-col min-w-[300px] bg-panel/30 backdrop-blur-xl border-l border-white/5">
          <div className="px-4 py-3 text-xs font-mono font-bold text-gray-500 uppercase tracking-widest shrink-0 border-b border-white/5">CONTEXT_DECK</div>
          <div className="flex-1 overflow-y-auto p-8 relative">
              <div className="absolute inset-0 opacity-[0.03] bg-[url('https://www.transparenttextures.com/patterns/graphy.png')] pointer-events-none"></div>
              <div className="text-center text-gray-500 font-mono text-sm">Document viewer disabled for now.</div>
          </div>
          <div className="h-8 border-t border-white/10 bg-black/40 flex items-center px-4 justify-between text-[10px] font-mono text-gray-500">
              <div className="flex items-center gap-2"><Database size={12} /><span>TOKENS: 0 / 128,000</span></div>
          </div>
      </div>
    </div>
  );
};

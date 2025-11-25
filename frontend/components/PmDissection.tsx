
import React, { useState } from 'react';
import { ClipboardList, ArrowRight, CheckSquare, GitBranch, AlertCircle, Sparkles, Database, FileJson } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';
import { ScrambleText } from './ScrambleText';

// --- Types ---

interface RawIdea {
  id: string;
  text: string;
  source: string;
}

interface StructuredTicket {
  idea_id: string;
  title: string;
  origin_story: string;
  category: 'New Standalone Project' | 'Feature for Existing Repo' | 'Infrastructure/DevOps' | 'Research Topic';
  implied_tasks: string[];
  potential_repo_links: string[];
  source_quotes: string;
}

// --- Mock Data ---

const RAW_INBOX: RawIdea[] = [
  { id: 'r1', text: "We should build a tool that generates PR descriptions from diffs automatically.", source: "mike_dev" },
  { id: 'r2', text: "Voice-to-Task extraction for engineering meetings would be cool.", source: "dave_arch" },
  { id: 'r3', text: "Need to automate the PDF metadata extraction manually, it's too slow.", source: "sarah_eng" }
];

const PROCESSED_TICKETS: Record<string, StructuredTicket> = {
  'r1': {
    idea_id: 'IDEA-042',
    title: 'Automated PR Description Generator',
    origin_story: 'Arose during a productivity discussion where mike_dev noted the inefficiency of writing manual PR summaries from large diffs.',
    category: 'Feature for Existing Repo',
    implied_tasks: [
      'Integrate GPT-4 Vision/Text API for diff analysis',
      'Create GitHub Action workflow trigger',
      'Implement template engine for output formatting',
      'Add "Regenerate" slash command comment listener'
    ],
    potential_repo_links: ['dev-ops-scripts', 'nexus-bot-core'],
    source_quotes: '"build a tool that generates PR descriptions from diffs automatically"'
  },
  'r2': {
    idea_id: 'IDEA-043',
    title: 'Voice-to-Task Meeting Processor',
    origin_story: 'Proposed by dave_arch as a Q4 goal to reduce administrative overhead from engineering syncs.',
    category: 'New Standalone Project',
    implied_tasks: [
      'Set up audio ingestion pipeline (LiveKit or S3 upload)',
      'Implement Whisper transcription service',
      'Design Entity Extraction prompt for "Action Items"',
      'Connect to Jira/Linear API for ticket creation'
    ],
    potential_repo_links: ['meeting-intel-service', 'New Repo'],
    source_quotes: '"listen to voice meetings and extract tasks directly"'
  },
  'r3': {
    idea_id: 'IDEA-044',
    title: 'PDF Metadata Extraction Pipeline',
    origin_story: 'Identified as a bottleneck by sarah_eng; current manual entry is slowing down the ingest rate.',
    category: 'Infrastructure/DevOps',
    implied_tasks: [
      'Evaluate OCR libraries (Tesseract vs AWS Textract)',
      'Define metadata schema (Author, Date, Version)',
      'Build background worker for batch processing',
      'Update Knowledge Graph ingestion hook'
    ],
    potential_repo_links: ['ingest-pipeline', 'knowledge-graph-api'],
    source_quotes: '"Need to automate the PDF metadata extraction manually"'
  }
};

export const PmDissection: React.FC = () => {
  const [inbox, setInbox] = useState<RawIdea[]>(RAW_INBOX);
  const [processed, setProcessed] = useState<StructuredTicket[]>([]);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const handleProcess = (rawId: string) => {
    if (processingId) return; // Busy
    setProcessingId(rawId);

    // Simulate AI "Thinking" delay
    setTimeout(() => {
      const ticket = PROCESSED_TICKETS[rawId];
      if (ticket) {
        setProcessed(prev => [ticket, ...prev]);
        setInbox(prev => prev.filter(i => i.id !== rawId));
      }
      setProcessingId(null);
    }, 2000);
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'New Standalone Project': return 'text-purple border-purple bg-purple/10';
      case 'Feature for Existing Repo': return 'text-cyan border-cyan bg-cyan/10';
      case 'Infrastructure/DevOps': return 'text-amber border-amber bg-amber/10';
      default: return 'text-gray-400 border-gray-400';
    }
  };

  return (
    <div className="h-[calc(100vh-140px)] w-full flex gap-6 animate-fade-in pb-4">
      
      {/* LEFT: Raw Inbox */}
      <div className="w-1/3 flex flex-col gap-4">
        <div>
          <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
             <AlertCircle className="text-gray-400" />
             UNSTRUCTURED_INBOX
          </h2>
          <p className="text-gray-500 font-mono text-xs mt-1">PENDING_PM_REVIEW: {inbox.length}</p>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto pr-2 custom-scrollbar">
          {inbox.length === 0 && (
            <div className="p-8 border border-dashed border-white/10 rounded-xl text-center text-gray-600 font-mono text-xs">
              NO_PENDING_ITEMS
            </div>
          )}
          {inbox.map(item => (
            <GlassCard key={item.id} variant="void" className="group hover:border-white/20 transition-all">
              <div className="flex justify-between items-start mb-2">
                 <span className="text-[10px] font-mono font-bold text-gray-500">ID: {item.id.toUpperCase()}</span>
                 <span className="text-[10px] font-mono text-cyan">@{item.source}</span>
              </div>
              <p className="text-sm text-gray-300 mb-4 leading-snug">"{item.text}"</p>
              <div className="flex justify-end">
                 <NeonButton 
                   variant="cyan" 
                   className="text-[10px] px-3 py-1.5" 
                   onClick={() => handleProcess(item.id)}
                   disabled={processingId !== null}
                 >
                   {processingId === item.id ? 'DISSECTING...' : 'DISSECT'}
                 </NeonButton>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>

      {/* CENTER: Visualization Arrow (Static for now, could be animated) */}
      <div className="w-16 flex flex-col items-center justify-center opacity-20">
         <ArrowRight size={32} className="text-white animate-pulse" />
      </div>

      {/* RIGHT: Structured Backlog */}
      <div className="flex-1 flex flex-col gap-4">
        <div>
          <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
             <ClipboardList className="text-green-400" />
             STRUCTURED_BACKLOG
          </h2>
          <p className="text-gray-500 font-mono text-xs mt-1">FORMAT: JSON_SCHEMA_V4</p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto pr-2 custom-scrollbar">
           {processed.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center border border-dashed border-white/10 rounded-xl bg-white/5 text-gray-500 gap-4">
                 <FileJson size={32} className="opacity-50" />
                 <div className="text-center">
                   <div className="text-sm font-mono">BACKLOG_EMPTY</div>
                   <div className="text-xs mt-1">Dissect raw ideas to generate tickets.</div>
                 </div>
              </div>
           )}

           {processed.map((ticket, idx) => (
             <div key={ticket.idea_id} className="animate-fade-in-up" style={{ animationDelay: `${idx * 100}ms` }}>
               <GlassCard variant="primary" className="relative overflow-hidden">
                  
                  {/* Decorative JSON Bracket */}
                  <div className="absolute top-2 right-2 text-[40px] font-mono text-white/5 font-bold leading-none pointer-events-none">{'}'}</div>

                  <div className="flex gap-4">
                     {/* Category Strip */}
                     <div className={`w-1 rounded-full ${ticket.category.includes('Infra') ? 'bg-amber' : ticket.category.includes('Feature') ? 'bg-cyan' : 'bg-purple'}`}></div>
                     
                     <div className="flex-1">
                        {/* Header */}
                        <div className="flex justify-between items-start mb-2">
                           <div>
                              <div className="flex items-center gap-2 mb-1">
                                 <span className="text-[10px] font-mono text-gray-500">{ticket.idea_id}</span>
                                 <span className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase border ${getCategoryColor(ticket.category)}`}>
                                    {ticket.category}
                                 </span>
                              </div>
                              <h3 className="text-lg font-bold text-white"><ScrambleText text={ticket.title} duration={500} /></h3>
                           </div>
                        </div>

                        {/* Origin Story */}
                        <div className="mb-4 text-xs text-gray-400 font-mono leading-relaxed border-l border-white/10 pl-3">
                           {ticket.origin_story}
                        </div>

                        {/* Tasks & Repos Grid */}
                        <div className="grid grid-cols-2 gap-4">
                           {/* Implied Tasks */}
                           <div className="bg-black/20 rounded p-3 border border-white/5">
                              <div className="text-[10px] uppercase tracking-widest text-gray-500 font-mono mb-2 flex items-center gap-2">
                                 <CheckSquare size={10} /> Implied Tasks
                              </div>
                              <ul className="space-y-1.5">
                                 {ticket.implied_tasks.map((task, i) => (
                                    <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                                       <span className="text-cyan mt-0.5">›</span>
                                       {task}
                                    </li>
                                 ))}
                              </ul>
                           </div>

                           {/* Repo Links */}
                           <div className="bg-black/20 rounded p-3 border border-white/5">
                              <div className="text-[10px] uppercase tracking-widest text-gray-500 font-mono mb-2 flex items-center gap-2">
                                 <GitBranch size={10} /> Target Repos
                              </div>
                              <div className="flex flex-wrap gap-2">
                                 {ticket.potential_repo_links.map((repo, i) => (
                                    <span key={i} className="px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] font-mono text-amber">
                                       {repo}
                                    </span>
                                 ))}
                              </div>
                           </div>
                        </div>

                        {/* Source Quote Footer */}
                        <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-2 text-[10px] text-gray-600 font-mono italic">
                           <Database size={10} />
                           Source: {ticket.source_quotes}
                        </div>
                     </div>
                  </div>
               </GlassCard>
             </div>
           ))}
        </div>
      </div>

    </div>
  );
};

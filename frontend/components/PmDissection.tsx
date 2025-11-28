import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ClipboardList, ArrowRight, GitBranch, AlertCircle, Sparkles, X, MessageSquare, Send, FileText, CheckCircle } from 'lucide-react';
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
  gap_analysis?: { missing_details: string[] };
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
    implied_tasks: ['Integrate GPT-4 Vision/Text API for diff analysis', 'Create GitHub Action workflow trigger', 'Implement template engine for output formatting', 'Add "Regenerate" slash command comment listener'],
    potential_repo_links: ['dev-ops-scripts', 'nexus-bot-core'],
    source_quotes: '"build a tool that generates PR descriptions from diffs automatically"'
  },
  'r2': {
    idea_id: 'IDEA-043',
    title: 'Voice-to-Task Meeting Processor',
    origin_story: 'Proposed by dave_arch as a Q4 goal to reduce administrative overhead from engineering syncs.',
    category: 'New Standalone Project',
    implied_tasks: ['Set up audio ingestion pipeline (LiveKit or S3 upload)', 'Implement Whisper transcription service', 'Design Entity Extraction prompt for "Action Items"', 'Connect to Jira/Linear API for ticket creation'],
    potential_repo_links: [],
    source_quotes: '"listen to voice meetings and extract tasks directly"',
    gap_analysis: { missing_details: ["Target Repository Not Defined", "Database Schema Missing"] }
  },
  'r3': {
    idea_id: 'IDEA-044',
    title: 'PDF Metadata Extraction Pipeline',
    origin_story: 'Identified as a bottleneck by sarah_eng; current manual entry is slowing down the ingest rate.',
    category: 'Infrastructure/DevOps',
    implied_tasks: ['Evaluate OCR libraries (Tesseract vs AWS Textract)', 'Define metadata schema (Author, Date, Version)', 'Build background worker for batch processing', 'Update Knowledge Graph ingestion hook'],
    potential_repo_links: ['ingest-pipeline', 'knowledge-graph-api'],
    source_quotes: '"Need to automate the PDF metadata extraction manually"'
  }
};

// --- Helper Functions ---
const generateMarkdown = (ticket: StructuredTicket): string => {
  return `
# ${ticket.title}

**ID:** ${ticket.idea_id}
**Category:** ${ticket.category}

## 1. Origin Story
> ${ticket.origin_story}
>
> *Source Quote: "${ticket.source_quotes}"*

## 2. Implied Tasks
${ticket.implied_tasks.map(task => `- [ ] ${task}`).join('\n')}

## 3. Technical Implementation
### Target Repositories
${ticket.potential_repo_links.length > 0 ? ticket.potential_repo_links.map(repo => `- \`${repo}\``).join('\n') : '*Not yet defined.*'}

### Data Schema
*Waiting for architectural review...*
  `;
};

// --- Split View Modal Component ---
const SplitViewModal = ({ ticket, onClose }: { ticket: StructuredTicket; onClose: () => void }) => {
  const [markdownContent, setMarkdownContent] = useState(generateMarkdown(ticket));
  const [chatMessages, setChatMessages] = useState<{ sender: 'user' | 'ai', text: string }[]>([]);
  const [chatInput, setChatInput] = useState('');

  const handleChatSend = () => {
    if (!chatInput.trim()) return;
    const newMessages = [...chatMessages, { sender: 'user' as 'user', text: chatInput }];
    setChatMessages(newMessages);
    setChatInput('');
    // Simulate AI response
    setTimeout(() => {
      setChatMessages(prev => [...prev, { sender: 'ai' as 'ai', text: `Acknowledged. I will update the spec based on your instruction: "${chatInput}"` }]);
    }, 1000);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-8"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="w-full max-w-6xl h-[90vh] bg-panel/80 border border-white/20 rounded-xl flex flex-col overflow-hidden shadow-2xl shadow-cyan/10"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex justify-between items-center p-4 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3">
            <FileText className="text-cyan" />
            <h2 className="font-mono text-lg text-white">{ticket.title}</h2>
            {ticket.gap_analysis && (
              <div className="flex items-center gap-1.5 ml-4 px-2 py-1 bg-amber/10 border border-amber/50 rounded-full text-xs font-mono text-amber">
                <AlertCircle size={14} />
                Gap Analysis: {ticket.gap_analysis.missing_details.join(', ')}
              </div>
            )}
          </div>
          <NeonButton variant="secondary" onClick={onClose} icon={<X size={16} />} className="px-3 py-2" />
        </header>

        <div className="flex-1 flex min-h-0">
          {/* Left Pane: Markdown Editor */}
          <div className="w-1/2 p-4 border-r border-white/10 overflow-y-auto custom-scrollbar">
            <textarea
              value={markdownContent}
              onChange={(e) => setMarkdownContent(e.target.value)}
              className="w-full h-full bg-transparent text-gray-300 font-mono text-sm resize-none focus:outline-none"
            />
          </div>

          {/* Right Pane: Chat */}
          <div className="w-1/2 flex flex-col">
            <div className="flex-1 p-4 space-y-4 overflow-y-auto custom-scrollbar">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`flex gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-3 rounded-lg text-sm ${msg.sender === 'user' ? 'bg-cyan/20 text-cyan' : 'bg-white/10 text-gray-300'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
               <div className="text-center text-gray-600 font-mono text-xs pt-4">Chat contextually linked to <br/>{ticket.idea_id}</div>
            </div>
            <div className="p-4 border-t border-white/10 shrink-0 flex items-center gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleChatSend()}
                placeholder="Instruct AI to refine the spec..."
                className="flex-1 bg-black/30 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan"
              />
              <NeonButton onClick={handleChatSend} icon={<Send size={14} />} className="px-4 py-2.5" />
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

// --- Main Component ---
export const PmDissection: React.FC = () => {
  const [inbox, setInbox] = useState<RawIdea[]>(RAW_INBOX);
  const [processed, setProcessed] = useState<StructuredTicket[]>([]);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<StructuredTicket | null>(null);

  const handleProcess = (rawId: string) => {
    if (processingId) return;
    setProcessingId(rawId);
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
      case 'New Standalone Project': return 'text-purple';
      case 'Feature for Existing Repo': return 'text-cyan';
      case 'Infrastructure/DevOps': return 'text-amber';
      default: return 'text-gray-400';
    }
  };

  return (
    <>
      <div className="h-[calc(100vh-140px)] w-full flex gap-6 animate-fade-in pb-4">
        {/* Left Column: Inbox */}
        <div className="w-1/3 flex flex-col gap-4">
           <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
              <AlertCircle className="text-gray-400" />
              UNSTRUCTURED_INBOX ({inbox.length})
           </h2>
           <div className="flex-1 space-y-3 overflow-y-auto pr-2 custom-scrollbar">
            {inbox.map(item => (
              <GlassCard key={item.id} variant="void" className="group hover:border-white/20 transition-all">
                <p className="text-sm text-gray-300 mb-2 leading-snug">"{item.text}"</p>
                <div className="flex justify-between items-center">
                   <span className="text-[10px] font-mono text-cyan">@{item.source}</span>
                   <NeonButton onClick={() => handleProcess(item.id)} disabled={!!processingId} className="text-[10px] px-3 py-1.5">
                     {processingId === item.id ? 'DISSECTING...' : 'DISSECT'}
                   </NeonButton>
                </div>
              </GlassCard>
            ))}
           </div>
        </div>

        {/* Center Arrow */}
        <div className="w-16 flex flex-col items-center justify-center opacity-20">
          <ArrowRight size={32} className="text-white animate-pulse" />
        </div>

        {/* Right Column: Structured Backlog */}
        <div className="flex-1 flex flex-col gap-4">
          <h2 className="text-xl font-mono text-white tracking-wide flex items-center gap-2">
            <ClipboardList className="text-green-400" />
            STRUCTURED_BACKLOG ({processed.length})
          </h2>
          <div className="flex-1 space-y-3 overflow-y-auto pr-2 custom-scrollbar">
            {processed.map((ticket, idx) => (
              <GlassCard
                key={ticket.idea_id}
                variant="primary"
                className="cursor-pointer group hover:!border-cyan"
                onClick={() => setSelectedTicket(ticket)}
              >
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="flex justify-between items-start"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${getCategoryColor(ticket.category).replace('text-', 'bg-')}`}></span>
                      <span className="font-mono text-xs text-gray-500">{ticket.idea_id}</span>
                       {ticket.gap_analysis && (
                        <div className="flex items-center gap-1 text-[9px] font-mono text-amber bg-amber/10 border border-amber/20 px-1.5 py-0.5 rounded-full">
                          <AlertCircle size={10} /> GAPS_DETECTED
                        </div>
                      )}
                    </div>
                    <h3 className="font-bold text-white mt-1">{ticket.title}</h3>
                  </div>
                  <div className="flex items-center gap-2 text-cyan opacity-0 group-hover:opacity-100 transition-opacity">
                    <span className="text-xs font-mono">EDIT_SPEC</span>
                    <ArrowRight size={14} />
                  </div>
                </motion.div>
              </GlassCard>
            ))}
          </div>
        </div>
      </div>
      
      {/* Modal */}
      <AnimatePresence>
        {selectedTicket && (
          <SplitViewModal 
            ticket={selectedTicket} 
            onClose={() => setSelectedTicket(null)} 
          />
        )}
      </AnimatePresence>
    </>
  );
};

import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, Cpu, Zap, X, Binary, Folder, FileCode, BotMessageSquare, Check, ChevronsRight, Loader } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { useIngestJobs, useDeleteIngestJob } from '@src/hooks/useIngestJobs';
import { useCurrentProject } from '@src/hooks/useProjects';
import { uploadIngestFile } from '@src/lib/cortexApi';
import { useQueryClient } from '@tanstack/react-query';
import { ErrorDisplay } from '../src/components/ErrorDisplay';
import { getErrorMessage } from '../src/lib/errorHandling';
import { NeonButton } from './NeonButton';

type ProcessingStage = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

interface IngestFile {
  id: string;
  name: string;
  progress: number;
  status: ProcessingStage;
}

// --- Bulk Import Wizard Components ---
const ProgressBar = ({ progress, label, icon }: { progress: number; label: string; icon: React.ReactNode }) => (
  <div className="w-full">
    <div className="flex items-center gap-2 mb-1.5 text-xs font-mono text-gray-300">
      {icon}
      <span>{label}</span>
      <span className="ml-auto text-cyan">{progress.toFixed(0)}%</span>
    </div>
    <div className="h-2 w-full bg-black/30 rounded-full overflow-hidden border border-white/10">
      <motion.div
        className="h-full bg-gradient-to-r from-cyan to-purple"
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 1, ease: 'easeInOut' }}
      />
    </div>
  </div>
);

const BulkImportWizard = ({ onClose }: { onClose: () => void }) => {
  const [step, setStep] = useState(1);
  const [scanComplete, setScanComplete] = useState(false);
  const [priorities, setPriorities] = useState<{ [key: string]: 'active' | 'archive' }>({
    'ai_studioNexusKnowledge': 'active',
    'old_project_gamma': 'archive',
  });
  const [isIngesting, setIsIngesting] = useState(false);
  const [progress, setProgress] = useState({ strategy: 0, reader: 0, coder: 0 });

  useEffect(() => {
    if (step === 1) {
      setTimeout(() => setScanComplete(true), 1500);
    }
    if (step === 3) {
      setIsIngesting(true);
      const interval = setInterval(() => {
        setProgress(p => ({
          strategy: Math.min(p.strategy + Math.random() * 20, 100),
          reader: Math.min(p.reader + Math.random() * 15, 100),
          coder: Math.min(p.coder + Math.random() * 10, 100),
        }));
      }, 500);
      return () => clearInterval(interval);
    }
  }, [step]);
  
  const allIngested = progress.strategy >= 100 && progress.reader >= 100 && progress.coder >= 100;

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-8"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }}
        className="w-full max-w-2xl bg-panel/90 border border-white/20 rounded-xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex justify-between items-center p-4 border-b border-white/10">
          <h2 className="font-mono text-lg text-white">Bulk Import Wizard: ~/takeout</h2>
          <NeonButton variant="secondary" onClick={onClose} icon={<X size={16} />} className="px-3 py-2" />
        </header>

        <div className="p-8">
          {/* Step 1: Scan */}
          {step === 1 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h3 className="text-xl font-bold text-center text-cyan mb-4">Step 1: Scanning Directory...</h3>
              {!scanComplete ? (
                <Loader className="mx-auto my-8 h-12 w-12 text-cyan animate-spin" />
              ) : (
                <AnimatePresence>
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <GlassCard><BotMessageSquare className="mx-auto mb-2 text-cyan" /> 42 Chat Logs</GlassCard>
                      <GlassCard><FileText className="mx-auto mb-2 text-purple" /> 112 Docs</GlassCard>
                      <GlassCard><FileCode className="mx-auto mb-2 text-amber" /> 12 Repos</GlassCard>
                    </div>
                    <NeonButton onClick={() => setStep(2)} className="w-full mt-8" icon={<ChevronsRight />}>Next: Set Priorities</NeonButton>
                  </motion.div>
                </AnimatePresence>
              )}
            </motion.div>
          )}
          {/* Step 2: Prioritize */}
          {step === 2 && (
             <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h3 className="text-xl font-bold text-center text-cyan mb-4">Step 2: Prioritize Projects</h3>
              <div className="space-y-3">
                {Object.keys(priorities).map(repo => (
                  <div key={repo} className="flex justify-between items-center p-3 bg-black/20 rounded-lg">
                    <span className="font-mono text-white">{repo}</span>
                    <div className="flex items-center gap-2">
                      <button onClick={() => setPriorities(p => ({...p, [repo]: 'active'}))} className={`px-3 py-1 text-xs rounded ${priorities[repo] === 'active' ? 'bg-green-500 text-black' : 'bg-white/10'}`}>Active</button>
                      <button onClick={() => setPriorities(p => ({...p, [repo]: 'archive'}))} className={`px-3 py-1 text-xs rounded ${priorities[repo] === 'archive' ? 'bg-gray-500 text-black' : 'bg-white/10'}`}>Archive</button>
                    </div>
                  </div>
                ))}
              </div>
              <NeonButton onClick={() => setStep(3)} className="w-full mt-8" icon={<ChevronsRight />}>Next: Begin Ingestion</NeonButton>
            </motion.div>
          )}
          {/* Step 3: Ingest */}
          {step === 3 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h3 className="text-xl font-bold text-center text-cyan mb-6">{allIngested ? "Ingestion Complete!" : "Step 3: Ingesting Streams..."}</h3>
              <div className="space-y-4">
                <ProgressBar progress={progress.strategy} label="Strategy Lane (Chat Logs)" icon={<BotMessageSquare size={14} />} />
                <ProgressBar progress={progress.reader} label="Super-Reader Lane (Docs)" icon={<FileText size={14} />} />
                <ProgressBar progress={progress.coder} label="Coder Lane (Repos)" icon={<FileCode size={14} />} />
              </div>
              {allIngested && (
                <motion.div initial={{opacity: 0}} animate={{opacity: 1}} className="text-center">
                  <Check className="mx-auto my-6 h-12 w-12 text-green-500" />
                  <NeonButton onClick={onClose} className="w-full mt-4" variant="primary">Finish</NeonButton>
                </motion.div>
              )}
            </motion.div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};


export const IngestStation: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isDeepScan, setIsDeepScan] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  
  const { project } = useCurrentProject();
  const projectId = project?.id;
  const queryClient = useQueryClient();
  const { data: jobsData, isLoading, error, refetch } = useIngestJobs(projectId);
  const deleteMutation = useDeleteIngestJob(projectId);

  const files: IngestFile[] = (jobsData?.items || []).map(job => ({
    id: job.id,
    name: job.source_path,
    progress: job.progress * 100,
    status: job.status.toUpperCase() as ProcessingStage,
  }));

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (!projectId) return;
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      // For simplicity, we just handle one file via drop
      const file = droppedFiles[0];
      try {
        await uploadIngestFile(projectId, file);
        queryClient.invalidateQueries({ queryKey: ['ingestJobs', { projectId }] });
      } catch (error) {
        console.error("Error uploading file:", error);
      }
    }
  }, [queryClient, projectId]);

  return (
    <>
      <div className="h-full flex flex-col gap-6 animate-fade-in pb-10">
        <div className="flex justify-between items-end">
           <div>
              <h2 className="text-2xl font-mono text-white tracking-wide">INGEST_STATION</h2>
              <p className="text-gray-500 font-mono text-xs mt-1">UNSTRUCTURED DATA PIPELINE</p>
           </div>
           <NeonButton onClick={() => setWizardOpen(true)} icon={<Folder size={14}/>}>
             Bulk Import from Takeout
           </NeonButton>
        </div>

        <div 
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`flex-1 min-h-[200px] border-2 border-dashed rounded-xl transition-all duration-300 flex flex-col items-center justify-center gap-4 group cursor-pointer relative overflow-hidden ${isDragging ? 'border-cyan bg-cyan/10' : 'border-white/20 hover:border-white/40 bg-white/5'}`}
        >
          <div className={`p-6 rounded-full border transition-all duration-300 ${isDragging ? 'scale-110 border-cyan text-cyan shadow-neon-cyan' : 'text-gray-400 group-hover:text-white border-white/10 bg-black/40'}`}>
            <Upload size={48} strokeWidth={1} />
          </div>
          <div className="text-center z-10">
            <h3 className={`text-xl font-mono font-bold tracking-widest mb-1 ${isDragging ? 'text-cyan' : 'text-white'}`}>
              SINGLE_FILE_INGEST
            </h3>
            <p className="text-gray-400 font-mono text-sm">Drag & drop a single PDF, document, or archive</p>
          </div>
        </div>

        {error && <ErrorDisplay error={error} onRetry={() => refetch()} title="Failed to load ingest jobs" />}

        {isLoading && <div className="text-gray-400 font-mono">Loading...</div>}
        {!error && files.length > 0 && (
          <div className="space-y-3">
             <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-widest px-1">
                <Binary size={14} /> Processing Queue ({files.length})
             </div>
             {files.map(file => (
               <GlassCard key={file.id} variant="void" className="p-3">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded border border-white/10 bg-white/5 text-cyan"><FileText size={16} /></div>
                  <div className="flex-1">
                    <span className="font-mono text-sm text-white truncate">{file.name}</span>
                     <div className="relative h-1.5 w-full bg-white/10 rounded-full overflow-hidden mt-1">
                        <div className="absolute h-full bg-gradient-to-r from-cyan to-blue-500" style={{ width: `${file.progress}%` }} />
                     </div>
                  </div>
                  <span className="font-mono text-[10px] uppercase">{file.status}</span>
                  <button onClick={() => deleteMutation.mutate(file.id)} className="p-1 hover:bg-red-500/20 rounded text-red-500"><X size={14} /></button>
                </div>
               </GlassCard>
             ))}
          </div>
        )}
      </div>
      
      <AnimatePresence>
        {wizardOpen && <BulkImportWizard onClose={() => setWizardOpen(false)} />}
      </AnimatePresence>
    </>
  );
};
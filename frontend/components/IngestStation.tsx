import React, { useState, useCallback, useEffect } from 'react';
import { Upload, FileText, Cpu, Zap, X, Binary } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { useIngestJobs, useDeleteIngestJob } from '../src/hooks/useIngestJobs';
import { useQueryClient } from '@tanstack/react-query';
import { ErrorDisplay } from '../src/components/ErrorDisplay';
import { getErrorMessage } from '../src/lib/errorHandling';

type ProcessingStage = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';

interface IngestFile {
  id: string;
  name: string;
  progress: number; // 0-100
  status: ProcessingStage;
}

export const IngestStation: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isDeepScan, setIsDeepScan] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  
  const projectId = "default_project";
  const queryClient = useQueryClient();
  const { data: jobsData, isLoading, error, refetch } = useIngestJobs(projectId);
  const deleteMutation = useDeleteIngestJob(projectId);
  
  // Show toast on delete error
  useEffect(() => {
    if (deleteMutation.error) {
      const toast = (window as any).__cortexToast;
      if (toast) {
        toast.error(getErrorMessage(deleteMutation.error));
      }
    }
  }, [deleteMutation.error]);

  const files: IngestFile[] = (jobsData?.items || []).map(job => ({
    id: job.id,
    name: job.source_path,
    progress: job.progress * 100,
    status: job.status.toUpperCase() as ProcessingStage,
  }));

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
        const formData = new FormData();
        formData.append("file", droppedFiles[0]);

        fetch("/api/ingest/upload", {
            method: "POST",
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            console.log("Upload successful, job created:", data.job_id);
            queryClient.invalidateQueries({ queryKey: ['ingestJobs', { projectId }] });
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Upload successful, job created:", data.job_id);
            queryClient.invalidateQueries({ queryKey: ['ingestJobs', { projectId }] });
            const toast = (window as any).__cortexToast;
            if (toast) {
                toast.success("File uploaded successfully");
            }
        })
        .catch(error => {
            console.error("Error uploading file:", error);
            const toast = (window as any).__cortexToast;
            if (toast) {
                toast.error(`Upload failed: ${getErrorMessage(error)}`);
            }
        });
    }
  }, [queryClient, projectId]);

  const removeFile = (id: string) => {
    setDeleteConfirm(id);
  };

  const confirmDelete = () => {
    if (deleteConfirm) {
      deleteMutation.mutate(deleteConfirm, {
        onSuccess: () => {
          setDeleteConfirm(null);
        },
        onError: (error) => {
          console.error("Failed to delete job:", error);
          // You could add a toast notification here
        },
      });
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm(null);
  };

  const getStageColor = (stage: ProcessingStage) => {
    switch(stage) {
      case 'RUNNING': return 'text-cyan';
      case 'COMPLETED': return 'text-green-500';
      case 'FAILED': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in pb-10">
      <div className="flex justify-between items-end">
         <div>
            <h2 className="text-2xl font-mono text-white tracking-wide">INGEST_STATION</h2>
            <p className="text-gray-500 font-mono text-xs mt-1">UNSTRUCTURED DATA PIPELINE // UPLOAD ZONE</p>
         </div>
         
         {/* Toggle Switch */}
         <div className="flex items-center gap-4 bg-panel border border-white/10 p-1 rounded-lg">
            <button 
              onClick={() => setIsDeepScan(false)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono transition-all ${!isDeepScan ? 'bg-cyan text-black shadow-neon-cyan' : 'text-gray-400 hover:text-white'}`}
            >
              <Zap size={14} />
              QUICK_INDEX
            </button>
            <button 
              onClick={() => setIsDeepScan(true)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono transition-all ${isDeepScan ? 'bg-purple text-white shadow-neon-purple' : 'text-gray-400 hover:text-white'}`}
            >
              <Cpu size={14} />
              DEEP_SCAN
            </button>
         </div>
      </div>

      {/* Drop Zone */}
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          flex-1 min-h-[300px] border-2 border-dashed rounded-xl transition-all duration-300 flex flex-col items-center justify-center gap-4 group cursor-pointer relative overflow-hidden
          ${isDragging 
            ? 'border-cyan bg-cyan/10 shadow-[inset_0_0_20px_rgba(0,240,255,0.2)]' 
            : 'border-white/20 hover:border-white/40 bg-white/5'}
        `}
      >
        {/* Animated grid background */}
        <div className="absolute inset-0 opacity-10 pointer-events-none" 
             style={{
               backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
               backgroundSize: '40px 40px',
               transform: isDragging ? 'scale(1.1)' : 'scale(1)',
               transition: 'transform 0.5s ease-out'
             }}
        />

        <div className={`p-6 rounded-full border border-white/10 bg-black/40 transition-all duration-300 ${isDragging ? 'scale-110 border-cyan text-cyan shadow-neon-cyan' : 'text-gray-400 group-hover:text-white'}`}>
           <Upload size={48} strokeWidth={1} />
        </div>
        
        <div className="text-center z-10">
          <h3 className={`text-xl font-mono font-bold tracking-widest mb-2 ${isDragging ? 'text-cyan' : 'text-white'}`}>
            FEED THE NEXUS
          </h3>
          <p className="text-gray-400 font-mono text-sm">
            Drag & drop PDF reports or codebases here
          </p>
          <p className="text-gray-600 text-xs mt-2 font-mono">
            PROTOCOL: {isDeepScan ? 'VISION_MODEL_ENABLED' : 'TEXT_PARSER_ONLY'}
          </p>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <ErrorDisplay
          error={error}
          onRetry={() => refetch()}
          title="Failed to load ingest jobs"
        />
      )}

      {/* File List */}
      {isLoading && <div className="text-gray-400 font-mono">Loading...</div>}
      {!error && files.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-widest px-1">
            <Binary size={14} />
            Processing Queue ({files.filter(f => f.status !== 'COMPLETED').length})
          </div>
          
          <div className="grid grid-cols-1 gap-3">
            {files.map(file => (
              <GlassCard key={file.id} variant="void" className="!p-0 overflow-hidden">
                <div className="p-4 flex items-center gap-4 relative">
                  {/* File Icon */}
                  <div className={`p-2 rounded border border-white/10 bg-white/5 ${file.status === 'COMPLETED' ? 'text-green-500' : 'text-cyan'}`}>
                    <FileText size={20} />
                  </div>
                  
                  {/* File Info & Progress Bar */}
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-mono text-sm text-white truncate">{file.name}</span>
                      <span className={`font-mono text-[10px] uppercase tracking-wider ${getStageColor(file.status)}`}>
                        {file.status === 'COMPLETED' ? 'INDEXED' : file.status}
                      </span>
                    </div>
                    
                    {/* Matrix Rain Progress Bar */}
                    <div className="relative h-2 w-full bg-white/10 rounded-full overflow-hidden">
                       <div 
                         className="absolute top-0 left-0 h-full transition-all duration-100 ease-linear flex items-center overflow-hidden"
                         style={{ width: `${file.progress}%` }}
                       >
                         {/* This creates the 'matrix rain' fill effect inside the bar */}
                         <div className={`w-full h-full ${file.status === 'COMPLETED' ? 'bg-green-500' : 'bg-cyan'}`}></div>
                         
                         {/* Optional: Add a texture overlay if we want more detail */}
                         <div className="absolute inset-0 w-full h-full opacity-30"
                              style={{ 
                                backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 2px, #000 2px, #000 4px)',
                                backgroundSize: '4px 100%' 
                              }}>
                         </div>
                       </div>
                       
                       {/* Glitch/Head indicator */}
                       {file.status !== 'COMPLETED' && (
                         <div 
                           className="absolute top-0 w-[2px] h-full bg-white shadow-[0_0_10px_white] z-10"
                           style={{ left: `${file.progress}%` }}
                         ></div>
                       )}
                    </div>
                    
                    <div className="flex justify-between items-center mt-1">
                       <span className="text-[10px] text-gray-500 font-mono"></span>
                       <span className="text-[10px] text-gray-500 font-mono">{Math.floor(file.progress)}%</span>
                    </div>
                  </div>

                  {/* Action */}
                  <button 
                    onClick={() => removeFile(file.id)}
                    disabled={file.status === 'RUNNING'}
                    className="p-2 hover:bg-white/10 rounded text-gray-500 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={file.status === 'RUNNING' ? 'Cannot delete running job. Cancel it first.' : 'Delete job'}
                  >
                    <X size={16} />
                  </button>

                  {/* Active Scanline for processing items */}
                  {file.status !== 'COMPLETED' && (
                    <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-cyan/50 animate-pulse"></div>
                  )}
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <GlassCard className="p-6 max-w-md">
            <h3 className="text-xl font-mono text-white mb-4">Confirm Deletion</h3>
            <p className="text-gray-400 mb-6">
              Are you sure you want to delete this ingest job? This action cannot be undone.
            </p>
            <div className="flex gap-4 justify-end">
              <button
                onClick={cancelDelete}
                className="px-4 py-2 bg-white/10 text-white rounded hover:bg-white/20 transition-colors font-mono"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors font-mono disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};
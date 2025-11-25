import React, { useState, useEffect, useCallback } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Cpu, Zap, X, Binary } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { NeonButton } from './NeonButton';

type ProcessingStage = 'QUEUED' | 'OCR_SCANNING' | 'MD_CONVERSION' | 'GRAPH_INDEXING' | 'COMPLETE';

interface IngestFile {
  id: string;
  name: string;
  size: string;
  type: string;
  progress: number; // 0-100
  stage: ProcessingStage;
  isDeepScan: boolean;
}

export const IngestStation: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isDeepScan, setIsDeepScan] = useState(false);
  const [files, setFiles] = useState<IngestFile[]>([]);

  // Simulate file processing
  useEffect(() => {
    const interval = setInterval(() => {
      setFiles(prevFiles => 
        prevFiles.map(file => {
          if (file.stage === 'COMPLETE') return file;

          // Processing logic simulation
          let nextProgress = file.progress + (file.isDeepScan ? 0.5 : 1.5); // Deep scan is slower
          let nextStage = file.stage;

          // Stage transitions based on progress
          if (nextProgress < 30) nextStage = 'OCR_SCANNING';
          else if (nextProgress < 70) nextStage = 'MD_CONVERSION';
          else if (nextProgress < 98) nextStage = 'GRAPH_INDEXING';
          
          if (nextProgress >= 100) {
            nextProgress = 100;
            nextStage = 'COMPLETE';
          }

          return { ...file, progress: nextProgress, stage: nextStage };
        })
      );
    }, 100);

    return () => clearInterval(interval);
  }, []);

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
    
    // Convert FileList to array and create IngestFile objects
    const droppedFiles = Array.from(e.dataTransfer.files).map((f: File) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: f.name,
      size: (f.size / 1024 / 1024).toFixed(2) + ' MB',
      type: f.type,
      progress: 0,
      stage: 'QUEUED' as ProcessingStage,
      isDeepScan: isDeepScan
    }));

    setFiles(prev => [...prev, ...droppedFiles]);
  }, [isDeepScan]);

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const getStageColor = (stage: ProcessingStage) => {
    switch(stage) {
      case 'OCR_SCANNING': return 'text-amber';
      case 'MD_CONVERSION': return 'text-purple';
      case 'GRAPH_INDEXING': return 'text-cyan';
      case 'COMPLETE': return 'text-green-500';
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

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-mono text-gray-400 uppercase tracking-widest px-1">
            <Binary size={14} />
            Processing Queue ({files.filter(f => f.stage !== 'COMPLETE').length})
          </div>
          
          <div className="grid grid-cols-1 gap-3">
            {files.map(file => (
              <GlassCard key={file.id} variant="void" className="!p-0 overflow-hidden">
                <div className="p-4 flex items-center gap-4 relative">
                  {/* File Icon */}
                  <div className={`p-2 rounded border border-white/10 bg-white/5 ${file.stage === 'COMPLETE' ? 'text-green-500' : 'text-cyan'}`}>
                    <FileText size={20} />
                  </div>
                  
                  {/* File Info & Progress Bar */}
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-mono text-sm text-white truncate">{file.name}</span>
                      <span className={`font-mono text-[10px] uppercase tracking-wider ${getStageColor(file.stage)}`}>
                        {file.stage === 'COMPLETE' ? 'INDEXED' : file.stage.replace('_', ' ')}
                      </span>
                    </div>
                    
                    {/* Matrix Rain Progress Bar */}
                    <div className="relative h-2 w-full bg-white/10 rounded-full overflow-hidden">
                       <div 
                         className="absolute top-0 left-0 h-full transition-all duration-100 ease-linear flex items-center overflow-hidden"
                         style={{ width: `${file.progress}%` }}
                       >
                         {/* This creates the 'matrix rain' fill effect inside the bar */}
                         <div className={`w-full h-full ${file.stage === 'COMPLETE' ? 'bg-green-500' : 'bg-cyan'}`}></div>
                         
                         {/* Optional: Add a texture overlay if we want more detail */}
                         <div className="absolute inset-0 w-full h-full opacity-30"
                              style={{ 
                                backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 2px, #000 2px, #000 4px)',
                                backgroundSize: '4px 100%' 
                              }}>
                         </div>
                       </div>
                       
                       {/* Glitch/Head indicator */}
                       {file.stage !== 'COMPLETE' && (
                         <div 
                           className="absolute top-0 w-[2px] h-full bg-white shadow-[0_0_10px_white] z-10"
                           style={{ left: `${file.progress}%` }}
                         ></div>
                       )}
                    </div>
                    
                    <div className="flex justify-between items-center mt-1">
                       <span className="text-[10px] text-gray-500 font-mono">{file.size}</span>
                       <span className="text-[10px] text-gray-500 font-mono">{Math.floor(file.progress)}%</span>
                    </div>
                  </div>

                  {/* Action */}
                  <button 
                    onClick={() => removeFile(file.id)}
                    className="p-2 hover:bg-white/10 rounded text-gray-500 hover:text-white transition-colors"
                  >
                    <X size={16} />
                  </button>

                  {/* Active Scanline for processing items */}
                  {file.stage !== 'COMPLETE' && (
                    <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-cyan/50 animate-pulse"></div>
                  )}
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
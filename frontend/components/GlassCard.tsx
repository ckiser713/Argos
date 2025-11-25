import React from 'react';

type CardVariant = 'primary' | 'void' | 'cyan' | 'amber' | 'purple';

interface GlassCardProps {
  children: React.ReactNode;
  title?: string;
  variant?: CardVariant;
  className?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({ 
  children, 
  title, 
  variant = 'primary',
  className = ''
}) => {
  
  // Mapping variant to gradient border colors
  const borderGradients = {
    primary: "from-white/10 via-white/5 to-white/10",
    void: "from-gray-800 to-black",
    cyan: "from-cyan/40 via-cyan/10 to-transparent",
    amber: "from-amber/40 via-amber/10 to-transparent",
    purple: "from-purple/40 via-purple/10 to-transparent",
  };

  const titleColors = {
    primary: "text-gray-400",
    void: "text-gray-500",
    cyan: "text-cyan",
    amber: "text-amber",
    purple: "text-purple",
  };

  return (
    <div className={`relative p-[1px] rounded-xl bg-gradient-to-br ${borderGradients[variant]} ${className}`}>
      <div className="bg-panel/80 backdrop-blur-md rounded-xl p-5 h-full w-full relative overflow-hidden">
        
        {/* Subtle decorative corner accent */}
        <div className={`absolute top-0 right-0 p-2 opacity-50`}>
             <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0 0H20V20" stroke="currentColor" className={titleColors[variant]} strokeWidth="1"/>
             </svg>
        </div>

        {title && (
          <div className={`font-mono text-xs font-bold tracking-[0.2em] mb-4 uppercase ${titleColors[variant]}`}>
            {title}
          </div>
        )}
        <div className="relative z-10">
          {children}
        </div>
      </div>
    </div>
  );
};
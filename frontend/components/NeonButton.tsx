import React from 'react';
import { useSound } from './SoundManager';

type ButtonVariant = 'cyan' | 'amber' | 'purple';

interface NeonButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  fullWidth?: boolean;
  icon?: React.ReactNode;
}

export const NeonButton: React.FC<NeonButtonProps> = ({ 
  children, 
  variant = 'cyan', 
  fullWidth = false,
  icon,
  className,
  onClick,
  onMouseEnter,
  ...props 
}) => {
  
  const { playClick, playHover } = useSound();

  const baseStyles = "relative px-6 py-3 font-mono text-sm font-bold uppercase tracking-wider transition-all duration-300 border focus:outline-none overflow-hidden group";
  
  const variantStyles = {
    cyan: "text-cyan border-cyan hover:bg-cyan hover:text-black hover:shadow-neon-cyan",
    amber: "text-amber border-amber hover:bg-amber hover:text-black hover:shadow-neon-amber",
    purple: "text-purple border-purple hover:bg-purple hover:text-white hover:shadow-neon-purple",
  };

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    playClick();
    if (onClick) onClick(e);
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    playHover();
    if (onMouseEnter) onMouseEnter(e);
  };

  return (
    <button 
      className={`
        ${baseStyles} 
        ${variantStyles[variant]} 
        ${fullWidth ? 'w-full' : ''} 
        ${className || ''}
      `}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      {...props}
    >
      <div className="relative z-10 flex items-center justify-center gap-2">
        {icon && <span>{icon}</span>}
        {children}
      </div>
      
      {/* Glitch effect overlay elements */}
      <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 skew-y-12"></div>
    </button>
  );
};
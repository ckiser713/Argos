import React, { useState, useEffect } from 'react';

interface ScrambleTextProps {
  text: string;
  duration?: number; // Total animation time in ms
  className?: string;
  preserveNumbers?: boolean; // If true, only scramble digits
}

const CHARS = 'ABCDEF0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
const DIGITS = '0123456789';

export const ScrambleText: React.FC<ScrambleTextProps> = ({ 
  text, 
  duration = 1000, 
  className = '',
  preserveNumbers = false
}) => {
  const [displayedText, setDisplayedText] = useState(text);

  useEffect(() => {
    let frame = 0;
    const fps = 30;
    const totalFrames = (duration / 1000) * fps;
    let intervalId: any;

    const animate = () => {
      setDisplayedText(prev => {
        return text.split('').map((char, index) => {
          if (char === ' ') return ' ';
          
          // Calculate progress for this character
          // Characters resolve from left to right roughly
          const progress = frame / totalFrames;
          const charThreshold = index / text.length;

          if (progress > charThreshold) {
            return char;
          }

          const pool = preserveNumbers ? DIGITS : CHARS;
          return pool[Math.floor(Math.random() * pool.length)];
        }).join('');
      });

      frame++;
      if (frame > totalFrames + 5) {
        clearInterval(intervalId);
        setDisplayedText(text); // Ensure final state is correct
      }
    };

    intervalId = setInterval(animate, 1000 / fps);

    return () => clearInterval(intervalId);
  }, [text, duration, preserveNumbers]);

  return (
    <span className={`font-mono ${className}`}>
      {displayedText}
    </span>
  );
};
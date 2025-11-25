import React, { useState, useEffect } from 'react';

interface TerminalTextProps {
  text: string;
  speed?: number;
  className?: string;
}

export const TerminalText: React.FC<TerminalTextProps> = ({ text, speed = 30, className = '' }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    setDisplayedText('');
    let index = 0;
    
    const intervalId = setInterval(() => {
      if (index < text.length) {
        setDisplayedText((prev) => prev + text.charAt(index));
        index++;
      } else {
        clearInterval(intervalId);
      }
    }, speed);

    return () => clearInterval(intervalId);
  }, [text, speed]);

  return (
    <span className={`font-mono ${className}`}>
      {displayedText}
    </span>
  );
};
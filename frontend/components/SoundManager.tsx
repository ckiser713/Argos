import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

interface SoundContextType {
  isEnabled: boolean;
  toggleSound: () => void;
  playClick: () => void;
  playHover: () => void;
  playScan: () => void;
}

const SoundContext = createContext<SoundContextType | undefined>(undefined);

export const useSound = () => {
  const context = useContext(SoundContext);
  if (!context) throw new Error('useSound must be used within a SoundProvider');
  return context;
};

export const SoundProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Initialize Audio Context on user interaction (handled by toggle)
  const initAudio = () => {
    if (!audioCtxRef.current) {
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContext) {
        audioCtxRef.current = new AudioContext();
      }
    }
  };

  const toggleSound = () => {
    initAudio();
    if (audioCtxRef.current?.state === 'suspended') {
      audioCtxRef.current.resume();
    }
    setIsEnabled(prev => !prev);
  };

  // Synth Helper: Simple Oscillator
  const playTone = (freq: number, type: OscillatorType, duration: number, gainVal: number = 0.1) => {
    if (!isEnabled || !audioCtxRef.current) return;

    try {
      const ctx = audioCtxRef.current;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      
      gain.gain.setValueAtTime(gainVal, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.warn("Audio play failed", e);
    }
  };

  const playClick = () => {
    // High-pitched blip
    playTone(1200, 'sine', 0.1, 0.05);
    // Slight noise crunch
    setTimeout(() => playTone(50, 'square', 0.05, 0.05), 10);
  };

  const playHover = () => {
    // Subtle low thrum
    playTone(200, 'sine', 0.05, 0.02);
  };

  const playScan = () => {
    // Arpeggio
    if (!isEnabled) return;
    let time = 0;
    [400, 600, 800, 1200].forEach(f => {
      setTimeout(() => playTone(f, 'sawtooth', 0.05, 0.03), time);
      time += 50;
    });
  };

  return (
    <SoundContext.Provider value={{ isEnabled, toggleSound, playClick, playHover, playScan }}>
      {children}
    </SoundContext.Provider>
  );
};
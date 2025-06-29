import React, { useState, useRef } from 'react';
import { speakText } from './speakText';

export const TTSButton = ({ text }) => {
  const [status, setStatus] = useState('idle'); // idle | processing | playing
  const audioRef = useRef(null);

  const handleClick = async () => {
    if (status === 'playing') {
      audioRef.current?.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      setStatus('idle');
      return;
    }

    setStatus('processing');
    try {
      const audio = await speakText(text);
      audioRef.current = audio;

      audio.onended = () => setStatus('idle');

      await audio.play();
      setStatus('playing');
    } catch (error) {
      setStatus('idle');
    }
  };

  return (
    <button onClick={handleClick} disabled={status === 'processing'}>
      {status === 'processing'
        ? 'Processing...'
        : status === 'playing'
        ? '⏹️ Stop'
        : '🔉 Play'}
    </button>
  );
};

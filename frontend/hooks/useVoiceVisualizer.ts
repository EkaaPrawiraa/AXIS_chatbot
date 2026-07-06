'use client';

import { useEffect, useRef, useState } from 'react';

type VisualizerState = 'idle' | 'listening' | 'processing' | 'speaking';

export function useVoiceVisualizer(state: VisualizerState) {
  const [audioLevel, setAudioLevel] = useState(0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    let stream: MediaStream | null = null;
    let audioContext: AudioContext | null = null;

    const stop = () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      stream?.getTracks().forEach((track) => track.stop());
      if (audioContext && audioContext.state !== 'closed') {
        void audioContext.close();
      }
    };

    if (state === 'listening') {
      const startMicLevel = async () => {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          if (cancelled) {
            stop();
            return;
          }

          audioContext = new AudioContext();
          const analyser = audioContext.createAnalyser();
          analyser.fftSize = 512;
          analyser.smoothingTimeConstant = 0.82;
          const source = audioContext.createMediaStreamSource(stream);
          source.connect(analyser);
          const samples = new Uint8Array(analyser.frequencyBinCount);

          const tick = () => {
            analyser.getByteTimeDomainData(samples);
            let sum = 0;
            for (const sample of samples) {
              const centered = (sample - 128) / 128;
              sum += centered * centered;
            }
            const rms = Math.sqrt(sum / samples.length);
            setAudioLevel(Math.min(1, rms * 4.8));
            frameRef.current = requestAnimationFrame(tick);
          };

          tick();
        } catch {
          setAudioLevel(0.36);
        }
      };

      void startMicLevel();
      return () => {
        cancelled = true;
        stop();
      };
    }

    if (state === 'processing' || state === 'speaking') {
      const startedAt = performance.now();
      const tick = (time: number) => {
        const elapsed = (time - startedAt) / 1000;
        const base =
          state === 'speaking'
            ? 0.34 + Math.sin(elapsed * 8.5) * 0.18 + Math.sin(elapsed * 17) * 0.08
            : 0.26 + Math.sin(elapsed * 5) * 0.08;
        setAudioLevel(Math.max(0.08, Math.min(1, base)));
        frameRef.current = requestAnimationFrame(tick);
      };
      frameRef.current = requestAnimationFrame(tick);
      return stop;
    }

    setAudioLevel(0.12);
    return stop;
  }, [state]);

  return audioLevel;
}

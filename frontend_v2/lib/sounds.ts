'use client';


type SoundKind = 'typing' | 'stream' | 'complete';

const SOUND_PROFILES: Record<SoundKind, { frequency: number; duration: number; gain: number; delay?: number }> = {
  typing: { frequency: 220, duration: 0.055, gain: 0.018 },
  stream: { frequency: 330, duration: 0.035, gain: 0.012 },
  complete: { frequency: 520, duration: 0.08, gain: 0.018, delay: 0.035 },
};

let audioContext: AudioContext | null = null;
let lastStreamTick = 0;

function getAudioContext() {
  if (typeof window === 'undefined') return null;
  const AudioCtor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtor) return null;
  audioContext ??= new AudioCtor();
  return audioContext;
}

function playTone(profile: { frequency: number; duration: number; gain: number; delay?: number }) {
  const context = getAudioContext();
  if (!context) return;
  const start = context.currentTime + (profile.delay ?? 0);
  const oscillator = context.createOscillator();
  const gain = context.createGain();

  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(profile.frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(profile.gain, start + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + profile.duration);

  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(start);
  oscillator.stop(start + profile.duration + 0.02);
}

export const chatSounds = {
  typing() {
    playTone(SOUND_PROFILES.typing);
  },
  stream() {
    const now = Date.now();
    if (now - lastStreamTick < 420) return;
    lastStreamTick = now;
    playTone(SOUND_PROFILES.stream);
  },
  complete() {
    playTone(SOUND_PROFILES.complete);
  },
};

export function dataUrlFromBase64(base64: string, format?: string) {
  const normalizedFormat = format || 'mpeg';
  const mime = normalizedFormat.includes('/') ? normalizedFormat : `audio/${normalizedFormat}`;
  return `data:${mime};base64,${base64}`;
}

export interface AudioHandle {
  done: Promise<void>;
  stop: () => void;
}

let activeAudioStop: (() => void) | null = null;

export function stopActiveAudio() {
  activeAudioStop?.();
  activeAudioStop = null;
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}


export function primeAudioElement(): HTMLAudioElement {
  const audio = new Audio();
  audio.muted = true;
  
  const primingPlay = audio.play();
  audio.pause();
  primingPlay.catch(() => undefined);
  audio.muted = false;
  return audio;
}

export function createAudioPlayer(src: string, onStarted?: () => void, reuse?: HTMLAudioElement): AudioHandle {
  stopActiveAudio();
  const audio = reuse || new Audio();
  audio.src = src;

  if (onStarted) {
    audio.addEventListener('playing', onStarted, { once: true });
  }

  const stop = () => {
    audio.pause();
    audio.currentTime = 0;
    if (activeAudioStop === stop) {
      activeAudioStop = null;
    }
  };

  activeAudioStop = stop;

  const done = new Promise<void>((resolve, reject) => {
    audio.addEventListener('ended', () => {
      if (activeAudioStop === stop) activeAudioStop = null;
      resolve();
    });
    audio.addEventListener('error', () => {
      if (activeAudioStop === stop) activeAudioStop = null;
      reject(new Error('Audio playback error'));
    });
    audio.play().catch((error) => {
      if (activeAudioStop === stop) activeAudioStop = null;
      reject(error);
    });
  });

  return {
    done,
    stop,
  };
}

export function playAudioSource(src: string): Promise<void> {
  return createAudioPlayer(src).done;
}

export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = String(reader.result || '');
      resolve(result.includes(',') ? result.split(',')[1] : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}


export async function blobToWavBlob(blob: Blob, targetRate = 16000): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const decodeCtx = new AudioContext();
  const decoded = await decodeCtx.decodeAudioData(arrayBuffer);
  await decodeCtx.close();

  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * targetRate), targetRate);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const rendered = await offline.startRendering();
  const samples = rendered.getChannelData(0);

  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeString = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, targetRate, true);
  view.setUint32(28, targetRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

export function speakWithBrowser(text: string, lang = 'id-ID') {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return false;
  }
  stopActiveAudio();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
  activeAudioStop = () => window.speechSynthesis.cancel();
  return true;
}

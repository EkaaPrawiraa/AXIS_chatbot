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

export function createAudioPlayer(src: string, onStarted?: () => void): AudioHandle {
  stopActiveAudio();
  const audio = new Audio(src);

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

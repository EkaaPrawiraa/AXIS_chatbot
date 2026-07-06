'use client';

import { Loader2, Mic, Send, Square } from '@/lib/assets';
import { useEffect, useRef, useState } from 'react';
import { animationClasses } from '@/lib/animations';
import { blobToBase64, blobToWavBlob } from '@/lib/audio';
import { voiceAPI } from '@/lib/api/voice';

const MIN_HEIGHT = 24;
const MAX_HEIGHT = 120;

type MicState = 'idle' | 'recording' | 'processing';

// auto-growing textarea + mic/send control. stays in normal flow (not fixed) so it tracks the real viewport bottom when
// the keyboard opens. mic here does inline speech-to-text into the textarea, separate from the header mic (Confession Space).
export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onFocusChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onFocusChange?: (focused: boolean) => void;
  disabled?: boolean;
}) {
  const hasText = Boolean(value.trim());
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [micState, setMicState] = useState<MicState>('idle');
  const [micError, setMicError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = `${MIN_HEIGHT}px`;
    el.style.height = `${Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, el.scrollHeight))}px`;
  }, [value]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const submit = () => {
    if (!hasText || disabled) return;
    onSubmit();
  };

  const startRecording = async () => {
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';
      const recorder = new MediaRecorder(stream, { mimeType });
      streamRef.current = stream;
      chunksRef.current = [];
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType });
        chunksRef.current = [];
        recorderRef.current = null;
        void processRecording(blob, blob.type || mimeType);
      };

      recorder.start();
      setMicState('recording');
    } catch {
      setMicError('Mikrofon tidak bisa diakses. Cek izin browser kamu ya.');
      setMicState('idle');
    }
  };

  const stopRecording = () => {
    setMicState('processing');
    recorderRef.current?.stop();
  };

  const processRecording = async (audio: Blob, mimeType: string) => {
    try {
      const wavBlob = await blobToWavBlob(audio).catch(() => audio);
      const audioBase64 = await blobToBase64(wavBlob);
      const result = await voiceAPI.transcribe({
        audio_base64: audioBase64,
        audio_mime: wavBlob.type || mimeType,
        language_pref: 'id',
      });
      if (result.voice_error || !result.text.trim()) {
        setMicError('Tidak bisa mendengar dengan jelas, coba lagi ya.');
      } else {
        onChange(value ? `${value} ${result.text.trim()}` : result.text.trim());
      }
    } catch {
      setMicError('Transkrip gagal. Cek koneksi kamu dan coba lagi.');
    } finally {
      setMicState('idle');
    }
  };

  const onMicClick = () => {
    if (micState === 'idle') void startRecording();
    else if (micState === 'recording') stopRecording();
  };

  const micLabel = micState === 'recording' ? 'Berhenti rekam' : micState === 'processing' ? 'Memproses...' : 'Rekam suara';

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className={`-mx-[22px] shrink-0 bg-[var(--v2-cream)] px-[22px] pb-[max(10px,env(safe-area-inset-bottom))] pt-2 ${animationClasses.composerIn}`}
    >
      {micError ? (
        <p className="mb-1.5 px-1 text-[12px] font-semibold text-[#a7462e]">{micError}</p>
      ) : null}
      <div className="flex items-end gap-2 rounded-[24px] border border-[var(--v2-line)] bg-[#fbf5ed]/95 px-4 py-2 shadow-[0_12px_32px_rgb(83_67_46_/_0.08)]">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onFocus={() => onFocusChange?.(true)}
          onBlur={() => onFocusChange?.(false)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          placeholder={micState === 'recording' ? 'Mendengarkan...' : 'Tulis pesan...'}
          disabled={disabled || micState !== 'idle'}
          className="min-w-0 flex-1 resize-none self-center bg-transparent text-[16px] font-medium leading-[1.4] text-[var(--v2-ink)] outline-none placeholder:text-[var(--v2-placeholder)]"
          style={{ height: MIN_HEIGHT, maxHeight: MAX_HEIGHT, overflowY: 'auto' }}
        />
        <button
          type={hasText ? 'submit' : 'button'}
          onClick={hasText ? undefined : onMicClick}
          disabled={disabled || (hasText ? false : micState === 'processing')}
          aria-label={hasText ? 'Kirim' : micLabel}
          className={`v2-anim-pressable grid h-[36px] w-[36px] shrink-0 place-items-center rounded-full text-[var(--v2-ink)] ${
            micState === 'recording' ? 'bg-[#a7462e]/12 text-[#a7462e]' : ''
          }`}
        >
          {hasText ? (
            <Send className="h-[18px] w-[18px]" />
          ) : micState === 'processing' ? (
            <Loader2 className="h-[18px] w-[18px] animate-spin" />
          ) : micState === 'recording' ? (
            <Square className="h-[16px] w-[16px]" fill="currentColor" />
          ) : (
            <Mic className="h-[20px] w-[20px]" strokeWidth={2.3} />
          )}
        </button>
      </div>
    </form>
  );
}

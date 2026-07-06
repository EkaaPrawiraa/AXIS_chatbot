'use client';

import { useState, useRef, useLayoutEffect } from 'react';
import { Mic, MicOff, Radio, Send } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useT } from '@/lib/i18n';
import type { VoiceInteractionStatus } from './VoiceInteractionPanel';

type ChatSpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: ChatSpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

type ChatSpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0: {
      transcript: string;
    };
  }>;
};

type ChatSpeechRecognitionConstructor = new () => ChatSpeechRecognitionLike;

type SpeechRecognitionWindow = Window & {
  SpeechRecognition?: ChatSpeechRecognitionConstructor;
  webkitSpeechRecognition?: ChatSpeechRecognitionConstructor;
};

interface ChatInputProps {
  onSend: (message: string) => void;
  onVoiceSend?: (audio: Blob, mimeType: string) => void;
  onVoiceStateChange?: (state: 'idle' | 'listening' | 'processing') => void;
  onToggleVoice?: () => void;
  voiceEnabled?: boolean;
  voiceStatus?: VoiceInteractionStatus;
  voiceTranscript?: string;
  voiceError?: string | null;
  isRecording?: boolean;
  isLoading?: boolean;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onVoiceStateChange,
  voiceEnabled = false,
  voiceStatus = 'idle',
  voiceTranscript,
  voiceError,
  isRecording: controlledIsRecording,
  isLoading,
  isStreaming,
  disabled = false,
  placeholder,
}: ChatInputProps) {
  const t = useT();
  const [message, setMessage] = useState('');
  const [localVoiceStatus, setLocalVoiceStatus] = useState<VoiceInteractionStatus>('idle');
  const [localVoiceError, setLocalVoiceError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<ChatSpeechRecognitionLike | null>(null);
  const speechBaseMessageRef = useRef('');
  const speechFinalTranscriptRef = useRef('');
  const recordingPointerIdRef = useRef<number | null>(null);
  const suppressNextActionClickRef = useRef(false);
  const isDisabled = disabled || isLoading || isStreaming;
  const effectiveVoiceStatus = localVoiceStatus !== 'idle' ? localVoiceStatus : voiceStatus;
  const isRecording = controlledIsRecording ?? effectiveVoiceStatus === 'listening';
  const voiceButtonDisabled = !voiceEnabled || isDisabled || Boolean(message.trim());

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const viewportCap = typeof window === 'undefined' ? 360 : Math.min(window.innerHeight * 0.42, 360);
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, viewportCap)}px`;
    textarea.style.overflowY = textarea.scrollHeight > viewportCap ? 'auto' : 'hidden';
  }, [message]);

  const handleSend = () => {
    if (message.trim() && !isDisabled) {
      onSend(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startHoldRecording = () => {
    if (voiceButtonDisabled || typeof window === 'undefined') return;

    const speechWindow = window as SpeechRecognitionWindow;
    const SpeechRecognition = (speechWindow.SpeechRecognition ||
      speechWindow.webkitSpeechRecognition) as ChatSpeechRecognitionConstructor | undefined;
    if (!SpeechRecognition) {
      setLocalVoiceError(t('voiceFailed'));
      return;
    }

    try {
      recognitionRef.current?.abort();
      const recognition = new SpeechRecognition();
      recognition.lang = 'id-ID';
      recognition.interimResults = true;
      recognition.continuous = true;
      speechBaseMessageRef.current = message.trimEnd();
      speechFinalTranscriptRef.current = '';
      setLocalVoiceError(null);
      setLocalVoiceStatus('listening');
      onVoiceStateChange?.('listening');

      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = speechFinalTranscriptRef.current;

        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result[0]?.transcript || '';
          if (result.isFinal) {
            finalTranscript = `${finalTranscript} ${transcript}`.trim();
          } else {
            interimTranscript = `${interimTranscript} ${transcript}`.trim();
          }
        }

        speechFinalTranscriptRef.current = finalTranscript;
        const nextTranscript = [finalTranscript, interimTranscript].filter(Boolean).join(' ').trim();
        const base = speechBaseMessageRef.current;
        setMessage([base, nextTranscript].filter(Boolean).join(base && nextTranscript ? ' ' : ''));
      };

      recognition.onerror = () => {
        setLocalVoiceError(t('voiceFailed'));
        setLocalVoiceStatus('idle');
        onVoiceStateChange?.('idle');
      };

      recognition.onend = () => {
        recognitionRef.current = null;
        setLocalVoiceStatus('idle');
        onVoiceStateChange?.('idle');
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (error) {
      console.error('Failed to start voice recording:', error);
      setLocalVoiceError(t('voiceFailed'));
      setLocalVoiceStatus('idle');
      onVoiceStateChange?.('idle');
    }
  };

  const stopHoldRecording = () => {
    if (localVoiceStatus !== 'listening') return;
    setLocalVoiceStatus('processing');
    onVoiceStateChange?.('processing');
    recognitionRef.current?.stop();
    window.setTimeout(() => {
      setLocalVoiceStatus('idle');
      onVoiceStateChange?.('idle');
      textareaRef.current?.focus();
    }, 220);
  };

  const handleVoicePointerDown = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (message.trim() || voiceButtonDisabled) return;
    event.preventDefault();
    suppressNextActionClickRef.current = true;
    recordingPointerIdRef.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    startHoldRecording();
  };

  const handleVoicePointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (recordingPointerIdRef.current !== event.pointerId) return;
    event.preventDefault();
    recordingPointerIdRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    stopHoldRecording();
  };

  const handleVoicePointerCancel = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (recordingPointerIdRef.current !== event.pointerId) return;
    recordingPointerIdRef.current = null;
    recognitionRef.current?.abort();
    setLocalVoiceStatus('idle');
    onVoiceStateChange?.('idle');
  };

  const handleVoiceKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (message.trim() || voiceButtonDisabled) return;
    if ((event.key === 'Enter' || event.key === ' ') && localVoiceStatus !== 'listening') {
      event.preventDefault();
      startHoldRecording();
    }
  };

  const handleVoiceKeyUp = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      stopHoldRecording();
    }
  };

  const voiceCopy = getVoiceCopy({
    t,
    status: effectiveVoiceStatus,
    isRecording,
    error: localVoiceError || voiceError,
    transcript: voiceTranscript,
  });
  const VoiceIcon = voiceCopy.Icon;
  const hasText = message.trim().length > 0;
  const sendDisabled = !message.trim() || isDisabled;
  const actionDisabled = hasText ? sendDisabled : voiceButtonDisabled;
  const micScale = effectiveVoiceStatus === 'listening' ? 1.08 : 1;
  const ActionIcon = hasText ? Send : VoiceIcon;
  const actionLabel = hasText ? t('sendToCreateConversation') : voiceCopy.hint;

  const handleActionClick = () => {
    if (suppressNextActionClickRef.current) {
      suppressNextActionClickRef.current = false;
      return;
    }
    if (hasText) {
      handleSend();
    }
  };

  return (
    <div className="relative">
      <div className="group/composer relative overflow-visible rounded-[1.65rem] border border-border/90 bg-card/96 p-3 shadow-[0_20px_70px_rgba(53,48,42,0.11)] backdrop-blur transition-[border-color,box-shadow,transform] duration-300 focus-within:border-ring/55 focus-within:ring-4 focus-within:ring-ring/10 sm:p-4">
        <div className="pointer-events-none absolute inset-x-6 bottom-full h-12 bg-[radial-gradient(circle_at_50%_100%,color-mix(in_oklab,var(--accent)_28%,transparent),transparent_70%)] opacity-0 transition-opacity duration-300 group-focus-within/composer:opacity-100" />

        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || t('shareThoughts')}
          disabled={isDisabled}
          rows={1}
          className={cn(
            'min-h-10 w-full resize-none bg-transparent px-1 pt-1 text-[16px] leading-6 outline-none placeholder:text-muted-foreground sm:text-[15px]',
            isDisabled && 'cursor-not-allowed opacity-50'
          )}
        />

        <div className="mt-3 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleActionClick}
            onPointerDown={hasText ? undefined : handleVoicePointerDown}
            onPointerUp={hasText ? undefined : handleVoicePointerUp}
            onPointerCancel={hasText ? undefined : handleVoicePointerCancel}
            onLostPointerCapture={hasText ? undefined : handleVoicePointerCancel}
            onKeyDown={hasText ? undefined : handleVoiceKeyDown}
            onKeyUp={hasText ? undefined : handleVoiceKeyUp}
            disabled={actionDisabled}
            title={actionLabel}
            aria-label={actionLabel}
            className={cn(
              'group/action relative flex size-11 shrink-0 items-center justify-center rounded-2xl border outline-none transition-[border-color,box-shadow,transform,background-color,color] duration-300 hover:-translate-y-0.5 active:scale-95 focus-visible:ring-4 focus-visible:ring-ring/12 sm:size-12',
              hasText
                ? 'border-primary bg-primary text-primary-foreground shadow-[var(--axis-shadow-soft)]'
                : isRecording || effectiveVoiceStatus !== 'idle'
                  ? 'border-primary bg-primary text-primary-foreground shadow-[0_14px_38px_rgba(53,48,42,0.18)]'
                  : 'border-border bg-muted/42 text-foreground hover:border-ring/45 hover:bg-muted/65',
              actionDisabled && 'cursor-not-allowed opacity-60 hover:translate-y-0 active:scale-100'
            )}
          >
            {!hasText && isRecording && (
              <span className="absolute inset-0 rounded-2xl border border-current opacity-30 animate-ping" />
            )}
            <span
              className="relative z-10 flex items-center justify-center transition-transform duration-200"
              style={{ transform: hasText ? undefined : `scale(${micScale})` }}
            >
              <ActionIcon className="size-4" />
            </span>
            <span className="pointer-events-none absolute bottom-full right-0 z-20 mb-3 w-[min(18rem,76vw)] translate-y-1 rounded-2xl border border-border bg-card/96 px-3.5 py-2 text-left text-xs font-medium leading-5 text-foreground opacity-0 shadow-[var(--axis-shadow)] backdrop-blur transition-[opacity,transform] duration-200 group-hover/action:translate-y-0 group-hover/action:opacity-100 group-focus-visible/action:translate-y-0 group-focus-visible/action:opacity-100">
              {actionLabel}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

function getVoiceCopy({
  t,
  status,
  isRecording,
  error,
  transcript,
}: {
  t: ReturnType<typeof useT>;
  status: VoiceInteractionStatus;
  isRecording: boolean;
  error?: string | null;
  transcript?: string;
}) {
  if (status === 'listening' || isRecording) {
    return {
      Icon: Radio,
      helper: transcript || t('voiceRecordingHelp'),
      hint: t('releaseToTranscribe'),
    };
  }

  if (status === 'processing') {
    return {
      Icon: Radio,
      helper: transcript || t('voiceProcessingMessage'),
      hint: t('voiceRoomProcessingHint'),
    };
  }

  if (status === 'speaking') {
    return {
      Icon: Radio,
      helper: transcript || t('audioAvailable'),
      hint: t('voiceSpeaking'),
    };
  }

  if (error) {
    return {
      Icon: MicOff,
      helper: error,
      hint: t('recordVoiceMessage'),
    };
  }

  return {
    Icon: Mic,
    helper: t('voiceIdleHelp'),
    hint: t('holdToRecordVoice'),
  };
}

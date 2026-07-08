'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft, Info, Mic, Square } from '@/lib/assets';
import { useEffect, useRef, useState } from 'react';
import { AuthRequired } from '@/components/session';
import { V2Shell } from '@/components/v2/V2Shell';
import { HotlineWarningCard } from '@/components/v2/chat/cards/HotlineWarningCard';
import { chatAPI } from '@/lib/api/chat';
import { voiceAPI } from '@/lib/api/voice';
import {
  blobToBase64,
  blobToWavBlob,
  createAudioPlayer,
  dataUrlFromBase64,
  primeAudioElement,
  speakWithBrowser,
  stopActiveAudio,
} from '@/lib/audio';
import { stripCrisisResourceBlock } from '@/lib/crisisResources';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import type { SendMessageResponse, TTSModelChoice } from '@/models';
import { useSessionStore } from '@/stores';
import { useUIStore } from '@/stores/ui';

type Phase = 'idle' | 'recording' | 'processing' | 'speaking';

const INTERIM_TRANSCRIBE_INTERVAL_MS = 2500;
const CAPTION_REVEAL_MIN_MS = 2200;
const CAPTION_REVEAL_MAX_MS = 9000;

export default function ConfessionSpacePage() {
  return (
    <AuthRequired>
      <ConfessionSpaceContent />
    </AuthRequired>
  );
}

function ConfessionSpaceContent() {
  const router = useRouter();
  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const addToast = useUIStore((state) => state.addToast);

  const [phase, setPhase] = useState<Phase>('idle');
  const [caption, setCaption] = useState('');
  const [captionSpeaker, setCaptionSpeaker] = useState<'user' | 'axis' | null>(null);
  const [showHotlineCard, setShowHotlineCard] = useState(false);

  const conversationIdRef = useRef<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const phq9StateRef = useRef<Record<string, unknown> | undefined>(undefined);
  const cbtStateRef = useRef<Record<string, unknown> | undefined>(undefined);
  const ephemeralHistoryRef = useRef<{role: string, content: string}[]>([]);

  const primedAudioRef = useRef<HTMLAudioElement | null>(null);

  const interimRecorderRef = useRef<MediaRecorder | null>(null);
  const interimChunksRef = useRef<BlobPart[]>([]);
  const interimActiveRef = useRef(false);
  const confirmedCaptionRef = useRef('');

  const ensureConversation = async () => {
    if (conversationIdRef.current) return conversationIdRef.current;
    if (!userId) return null;
    const conversation = await chatAPI.createConversation(userId, 'Confession Space', 'confession');
    conversationIdRef.current = conversation.id;
    return conversationIdRef.current;
  };

  const clearRevealTimer = () => {
    if (revealTimerRef.current) {
      clearTimeout(revealTimerRef.current);
      revealTimerRef.current = null;
    }
  };

  const preferredMimeType = () =>
    MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';

  const runInterimSegment = (stream: MediaStream) => {
    if (!interimActiveRef.current) return;
    let segmentRecorder: MediaRecorder;
    try {
      segmentRecorder = new MediaRecorder(stream, { mimeType: preferredMimeType() });
    } catch (error) {
      console.warn('Confession Space: interim recorder failed to start', error);
      return;
    }
    interimRecorderRef.current = segmentRecorder;
    interimChunksRef.current = [];

    segmentRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) interimChunksRef.current.push(event.data);
    };
    segmentRecorder.onstop = () => {
      void (async () => {
        const chunks = interimChunksRef.current;
        interimChunksRef.current = [];
        if (chunks.length > 0) {
          try {
            const blob = new Blob(chunks, { type: segmentRecorder.mimeType || 'audio/webm' });
            const audioBase64 = await blobToBase64(blob);
            const result = await voiceAPI.transcribe({
              audio_base64: audioBase64,
              audio_mime: blob.type || 'audio/webm',
              language_pref: user?.preferredLanguage || 'id',
            });
            const text = result.text?.trim();
            if (text) {
              confirmedCaptionRef.current = confirmedCaptionRef.current
                ? `${confirmedCaptionRef.current} ${text}`
                : text;
              setCaption(confirmedCaptionRef.current);
              setCaptionSpeaker('user');
            }
          } catch (error) {
            console.warn('Confession Space: interim transcribe segment failed', error);
          }
        }
        
        if (interimActiveRef.current) runInterimSegment(stream);
      })();
    };
    segmentRecorder.start();
    setTimeout(() => {
      if (segmentRecorder.state === 'recording') segmentRecorder.stop();
    }, INTERIM_TRANSCRIBE_INTERVAL_MS);
  };

  const startRecording = async () => {
    if (phase !== 'idle') return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: preferredMimeType() });
      streamRef.current = stream;
      chunksRef.current = [];
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.start(250);
      setPhase('recording');
      setCaption('');
      setCaptionSpeaker('user');
      confirmedCaptionRef.current = '';
      interimActiveRef.current = true;
      runInterimSegment(stream);
    } catch {
      addToast('Mikrofon tidak bisa diakses. Cek izin browser kamu ya.', 'error');
    }
  };

  const stopRecording = () => {
    if (phase !== 'recording') return;
    // Prime here, synchronously, still inside this click — AXIS's spoken
    // reply won't be ready until sendTurn's full network round trip
    // finishes several awaits from now.
    primedAudioRef.current = primeAudioElement();
    interimActiveRef.current = false;
    if (interimRecorderRef.current?.state === 'recording') {
      // Its own onstop will fire and see interimActiveRef=false, so it
      // transcribes this last segment once more without rescheduling.
      interimRecorderRef.current.stop();
    }
    const recorder = recorderRef.current;
    const stream = streamRef.current;
    if (!recorder) return;
    setPhase('processing');
    recorder.onstop = () => {
      stream?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
      chunksRef.current = [];
      recorderRef.current = null;
      void sendTurn(blob, blob.type);
    };
    recorder.stop();
  };

  const revealCaptionOverAudio = (text: string, durationMs: number) => {
    clearRevealTimer();
    const words = text.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      setCaption('');
      return;
    }
    const step = Math.max(1, Math.floor(durationMs / words.length));
    let index = 0;
    const tick = () => {
      index += 1;
      setCaption(words.slice(0, index).join(' '));
      if (index < words.length) {
        revealTimerRef.current = setTimeout(tick, step);
      }
    };
    tick();
  };

  const sendTurn = async (audio: Blob, mimeType: string) => {
    if (!userId) return;
    setShowHotlineCard(false);
    try {
      const conversationId = await ensureConversation();
      if (!conversationId) return;
      const audioBase64 = await blobToBase64(audio);
      const response: SendMessageResponse = await chatAPI.sendMessage({
        conversationId,
        content: '',
        userId,
        language_pref: user?.preferredLanguage || 'id',
        single_pass_voice: true,
        ephemeral_history: ephemeralHistoryRef.current,
        phq9_state: phq9StateRef.current,
        cbt_state: cbtStateRef.current,
        voice: {
          output_modality: 'both',
          audio_input_base64: audioBase64,
          audio_input_mime: audio.type || mimeType || 'audio/webm',
          voice_id: user?.preferredVoiceId,
          tts_model: (user?.preferredTtsModel || 'v2_5_turbo') as TTSModelChoice,
        },
      });
      if (response.phq9_state !== undefined) phq9StateRef.current = response.phq9_state;
      if (response.cbt_state !== undefined) cbtStateRef.current = response.cbt_state;
      const crisisTier = response.crisis_tier || response.assistantMessage?.metadata?.crisisTier;
      if (crisisTier === '1' || crisisTier === '2') setShowHotlineCard(true);

      const userText = response.voice?.transcript || response.userMessage?.content || '';
      if (userText) {
        setCaption(userText);
        setCaptionSpeaker('user');
      }

      const rawAssistantText = response.assistantMessage?.content || response.reply || '';

      const assistantText = stripCrisisResourceBlock(rawAssistantText);
      const spokenText = response.voice?.speech_response || rawAssistantText;

      if (userText || rawAssistantText) {
        // Append to our ephemeral history so the next turn has context
        const newHistory = [...ephemeralHistoryRef.current];
        if (userText) newHistory.push({ role: 'user', content: userText });
        if (rawAssistantText) newHistory.push({ role: 'assistant', content: rawAssistantText });
        ephemeralHistoryRef.current = newHistory;
      }

      const source = response.voice?.audio_output_base64
        ? dataUrlFromBase64(response.voice.audio_output_base64, response.voice.audio_output_format)
        : response.voice?.audio_output_url || null;

      setPhase('speaking');
      setCaptionSpeaker('axis');

      if (source) {
        const probe = new Audio(source);
        const durationMs = await new Promise<number>((resolve) => {
          probe.addEventListener('loadedmetadata', () => resolve(probe.duration * 1000), { once: true });
          probe.addEventListener('error', () => resolve(0), { once: true });
        });
        const revealMs = Math.min(
          CAPTION_REVEAL_MAX_MS,
          Math.max(CAPTION_REVEAL_MIN_MS, durationMs || assistantText.length * 55)
        );
        revealCaptionOverAudio(assistantText, revealMs);
        try {
          await createAudioPlayer(source, undefined, primedAudioRef.current || undefined).done;
        } catch {
          if (spokenText) speakWithBrowser(spokenText, user?.preferredLanguage === 'en' ? 'en-US' : 'id-ID');
        }
      } else {
        const revealMs = Math.min(CAPTION_REVEAL_MAX_MS, Math.max(CAPTION_REVEAL_MIN_MS, assistantText.length * 55));
        revealCaptionOverAudio(assistantText, revealMs);
        if (spokenText) speakWithBrowser(spokenText, user?.preferredLanguage === 'en' ? 'en-US' : 'id-ID');
        await new Promise((resolve) => setTimeout(resolve, revealMs));
      }
    } catch (error) {
      addToast(friendlyErrorMessage(error, 'Suaramu belum berhasil diproses. Coba lagi sebentar ya.'), 'error');
    } finally {
      setPhase('idle');
    }
  };

  const onMicClick = () => {
    if (phase === 'idle') void startRecording();
    else if (phase === 'recording') stopRecording();
  };

  useEffect(() => {
    return () => {
      interimActiveRef.current = false;
      if (interimRecorderRef.current?.state === 'recording') {
        interimRecorderRef.current.onstop = null;
        interimRecorderRef.current.stop();
      }
      clearRevealTimer();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      stopActiveAudio();
    };
  }, []);

  const micLabel =
    phase === 'recording'
      ? 'Ketuk untuk berhenti & proses'
      : phase === 'processing'
        ? 'Memproses...'
        : phase === 'speaking'
          ? 'AXIS sedang bicara'
          : 'Ketuk untuk mulai cerita';

  return (
    <V2Shell showTopbar={false} showBottomNav={false}>
      <main className="fixed inset-0 z-40 flex flex-col items-center overflow-y-auto bg-[var(--v2-c-151210)] px-5 pb-[calc(1.5rem+env(safe-area-inset-bottom))] pt-[calc(1rem+env(safe-area-inset-top))] text-center">
        <div className="flex w-full items-center justify-between">
          <button
            onClick={() => router.push('/')}
            aria-label="Kembali"
            className="v2-anim-pressable grid h-[42px] w-[42px] place-items-center rounded-full bg-white/10 text-white"
          >
            <ArrowLeft className="h-[19px] w-[19px]" />
          </button>
          <p className="flex items-center gap-1 text-[11px] font-medium text-white/40">
            <Info className="h-[11px] w-[11px]" /> Percakapan ini tidak akan disimpan
          </p>
        </div>

        <div className="flex w-full flex-1 flex-col items-center justify-center gap-8">
          <button
            onClick={onMicClick}
            disabled={phase === 'processing' || phase === 'speaking'}
            aria-label={micLabel}
            className={`v2-anim-pressable grid h-[92px] w-[92px] place-items-center rounded-full shadow-[0_18px_34px_-16px_rgba(var(--v2-rgb-000000),0.6)] disabled:opacity-60 ${
              phase === 'recording' ? 'bg-[var(--v2-clay)]' : 'bg-white'
            }`}
          >
            {phase === 'recording' ? (
              <Square className="h-[30px] w-[30px] text-white" fill="currentColor" />
            ) : (
              <Mic className={`h-[34px] w-[34px] ${phase === 'idle' ? 'text-[var(--v2-ink)]' : 'text-white/60'}`} />
            )}
          </button>

          <p className="text-[12.5px] font-medium text-white/60">{micLabel}</p>
        </div>


        <div className="flex min-h-[110px] w-full items-center justify-center px-4">
          {caption ? (
            <p
              className={`text-center text-[19px] font-semibold leading-snug ${
                captionSpeaker === 'axis' ? 'text-[var(--v2-c-f7d774)]' : 'text-white'
              }`}
            >
              {caption}
            </p>
          ) : (
            <p className="text-center text-[14px] font-medium text-white/50">
              {phase === 'recording'
                ? 'Mendengarkan...'
                : phase === 'processing'
                  ? 'Memproses...'
                  : phase === 'speaking'
                    ? 'AXIS sedang bicara...'
                    : 'Ketuk mic untuk mulai bercerita.'}
            </p>
          )}
        </div>

        {showHotlineCard ? (
          <div className="pt-3">
            <HotlineWarningCard />
          </div>
        ) : null}
      </main>
    </V2Shell>
  );
}

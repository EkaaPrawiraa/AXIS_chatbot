'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { AppShell } from '@/components/layout';
import { VoiceInteractionStatus, VoiceRoom } from '@/components/chat';
import { useChatMessages, useConversations, useCreateConversation, useSendMessage } from '@/hooks';
import { usePreferencesStore, useSessionStore } from '@/stores';
import { ID, Message, SendMessageResponse } from '@/models';
import { blobToBase64, createAudioPlayer, dataUrlFromBase64, speakWithBrowser, stopActiveAudio } from '@/lib/audio';
import { chatAPI } from '@/lib/api/chat';
import { useT } from '@/lib/i18n';

export default function VoiceRoomPage() {
  return (
    <AppShell>
      <VoiceRoomContent />
    </AppShell>
  );
}

function VoiceRoomContent() {
  const t = useT();
  const router = useRouter();
  const queryClient = useQueryClient();
  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const isInitialized = useSessionStore((state) => state.isInitialized);
  const createConversationMutation = useCreateConversation();
  const sendMessageMutation = useSendMessage();
  const activeUserId = isAuthenticated ? userId : null;
  const { data: conversations = [] } = useConversations(activeUserId);
  const chatResponseMode = usePreferencesStore((state) => state.chatResponseMode);

  const [conversationId, setConversationId] = useState<ID | null>(null);
  const [status, setStatus] = useState<VoiceInteractionStatus>('idle');
  const [isRecording, setIsRecording] = useState(false);
  const [conversationActive, setConversationActive] = useState(false);
  const [voiceLevel, setVoiceLevel] = useState(0.12);
  const [userTranscript, setUserTranscript] = useState('');
  const [assistantTranscript, setAssistantTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showMiniSession, setShowMiniSession] = useState(false);
  const [lockedConversationId, setLockedConversationId] = useState<ID | null>(null);
  const activeSessionId = lockedConversationId || conversationId;
  const preferredResponseModel = profile?.preferredResponseModel || user?.preferredResponseModel;
  const { data: sessionMessages = [] } = useChatMessages(activeSessionId, 1, 100, Boolean(activeSessionId));

  const recorderRef = useRef<MediaRecorder | null>(null);
  const voiceChunksRef = useRef<BlobPart[]>([]);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const conversationActiveRef = useRef(false);
  const lockedConversationIdRef = useRef<ID | null>(null);
  const phq9StateByConversationRef = useRef<Record<string, Record<string, unknown> | undefined>>({});
  const cbtStateByConversationRef = useRef<Record<string, Record<string, unknown> | undefined>>({});
  const shouldProcessStopRef = useRef(false);
  const analyserFrameRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioPlaybackRef = useRef<HTMLAudioElement | null>(null);
  const audioPlaybackResolveRef = useRef<(() => void) | null>(null);
  const audioUnlockedRef = useRef(false);
  const listeningLockedRef = useRef(false);

  const AI_TAIL_PADDING_MS = 450;
  const POST_AI_LISTEN_DELAY_MS = 2000;
  const USER_TRANSCRIPT_PREVIEW_MS = 1200;

  const STREAM_REVEAL_INTERVAL_MS = 36;
  const streamPendingRef = useRef('');
  const streamRevealedRef = useRef('');
  const streamDrainTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.replace('/auth?next=/voice-room');
    }
  }, [isAuthenticated, isInitialized, router]);

  const stopStreamDrainer = () => {
    if (streamDrainTimerRef.current) {
      clearInterval(streamDrainTimerRef.current);
      streamDrainTimerRef.current = null;
    }
  };

  const startStreamDrainer = () => {
    if (streamDrainTimerRef.current) return;
    streamDrainTimerRef.current = setInterval(() => {
      const target = streamPendingRef.current;
      const current = streamRevealedRef.current;
      if (current.length >= target.length) return;
      const next = target.slice(0, current.length + 1);
      streamRevealedRef.current = next;
      setAssistantTranscript(next);
    }, STREAM_REVEAL_INTERVAL_MS);
  };

  const resetStreamDrainer = () => {
    stopStreamDrainer();
    streamPendingRef.current = '';
    streamRevealedRef.current = '';
  };

  const clearSubtitleLater = (delayMs = 3000) => {
    if (clearTimerRef.current) {
      clearTimeout(clearTimerRef.current);
    }
    clearTimerRef.current = setTimeout(() => {
      setUserTranscript('');
      setAssistantTranscript('');
      setError(null);
    }, delayMs);
  };

  const ensureConversation = async () => {
    if (!userId) return null;
    if (lockedConversationIdRef.current) return lockedConversationIdRef.current;
    if (lockedConversationId) return lockedConversationId;
    if (conversationId) {
      lockedConversationIdRef.current = conversationId;
      return conversationId;
    }

    const conversation = await createConversationMutation.mutateAsync({
      userId,
      title: t('voiceRoom'),
    });
    lockedConversationIdRef.current = conversation.id;
    setConversationId(conversation.id);
    setLockedConversationId(conversation.id);
    return conversation.id;
  };

  const unlockAudioPlayback = () => {
    if (audioUnlockedRef.current || typeof window === 'undefined') return;

    const audio = audioPlaybackRef.current || new Audio();
    audioPlaybackRef.current = audio;
    audio.preload = 'auto';
    audio.muted = true;
    audio.setAttribute('playsinline', 'true');
    audio.src =
      'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=';
    void audio
      .play()
      .then(() => {
        audio.pause();
        audio.currentTime = 0;
        audio.muted = false;
        audioUnlockedRef.current = true;
      })
      .catch(() => {
        audio.muted = false;
      });
  };

  const playVoiceSource = (src: string) => {
    const player = createAudioPlayer(src);
    audioPlaybackResolveRef.current = player.stop;
    return player.done.finally(() => {
      if (audioPlaybackResolveRef.current === player.stop) {
        audioPlaybackResolveRef.current = null;
      }
    });
  };

  const stopVoicePlayback = () => {
    const audio = audioPlaybackRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      audioPlaybackResolveRef.current?.();
      audioPlaybackResolveRef.current = null;
    }
    stopActiveAudio();
  };

  const stopAudioAnalysis = () => {
    if (analyserFrameRef.current) {
      cancelAnimationFrame(analyserFrameRef.current);
      analyserFrameRef.current = null;
    }
    const audioContext = audioContextRef.current;
    audioContextRef.current = null;
    if (audioContext && audioContext.state !== 'closed') {
      void audioContext.close();
    }
    setVoiceLevel(0.12);
  };

  const stopCurrentRecording = (processAudio: boolean) => {
    shouldProcessStopRef.current = processAudio;
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
    voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    stopAudioAnalysis();
    voiceStreamRef.current = null;
    setIsRecording(false);
  };

  const startSilenceDetection = (stream: MediaStream) => {
    stopAudioAnalysis();
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.76;
    audioContext.createMediaStreamSource(stream).connect(analyser);
    audioContextRef.current = audioContext;

    const samples = new Uint8Array(analyser.frequencyBinCount);
    const startedAt = performance.now();
    let lastVoiceAt = performance.now();
    let heardVoice = false;

    const tick = () => {
      analyser.getByteTimeDomainData(samples);
      let sum = 0;
      for (const sample of samples) {
        const centered = (sample - 128) / 128;
        sum += centered * centered;
      }
      const rms = Math.sqrt(sum / samples.length);
      const normalized = Math.min(1, rms * 6.2);
      const now = performance.now();
      setVoiceLevel(Math.max(0.08, normalized));

      if (normalized > 0.12) {
        heardVoice = true;
        lastVoiceAt = now;
      }

      if (conversationActiveRef.current && heardVoice && now - lastVoiceAt > 3000 && now - startedAt > 1200) {
        stopCurrentRecording(true);
        return;
      }

      analyserFrameRef.current = requestAnimationFrame(tick);
    };

    tick();
  };

  const startListeningCycle = async () => {
    if (!userId) {
      router.push('/auth?next=/voice-room');
      return;
    }
    if (!conversationActiveRef.current || isRecording || status === 'processing' || status === 'speaking') return;
    if (listeningLockedRef.current) return;

    try {
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current);
      }
      setError(null);
      setUserTranscript('');
      setAssistantTranscript('');

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/mp4')
          ? 'audio/mp4'
          : 'audio/webm';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      voiceStreamRef.current = stream;
      voiceChunksRef.current = [];
      recorderRef.current = recorder;
      shouldProcessStopRef.current = false;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) voiceChunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        voiceStreamRef.current = null;
        stopAudioAnalysis();
        const blob = new Blob(voiceChunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' });
        voiceChunksRef.current = [];
        recorderRef.current = null;
        setIsRecording(false);

        if (shouldProcessStopRef.current && blob.size > 0 && conversationActiveRef.current) {
          void handleSendVoice(blob, blob.type || mimeType || 'audio/webm');
        } else if (!conversationActiveRef.current) {
          setStatus('idle');
        }
      };

      recorder.start(250);
      setIsRecording(true);
      setStatus('listening');
      startSilenceDetection(stream);
    } catch (voiceError) {
      console.error('Failed to start voice room recording:', voiceError);
      setError(t('voiceFailed'));
      setIsRecording(false);
      setConversationActive(false);
      conversationActiveRef.current = false;
      setStatus('idle');
    }
  };

  const handleSendVoice = async (audio: Blob, mimeType: string) => {
    if (!userId) {
      router.push('/auth?next=/voice-room');
      return;
    }

    try {
      setError(null);
      setStatus('processing');
      listeningLockedRef.current = true;
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
      }
      const targetConversationId = await ensureConversation();
      if (!targetConversationId) return;

      const audioBase64 = await blobToBase64(audio);
      const sendPayload = {
        conversationId: targetConversationId,
        content: '',
        userId,
        language_pref: user?.preferredLanguage || 'id',
        preferred_response_model: preferredResponseModel,
        phq9_state: phq9StateByConversationRef.current[targetConversationId],
        cbt_state: cbtStateByConversationRef.current[targetConversationId],
        voice: {
          output_modality: 'both' as const,
          audio_input_base64: audioBase64,
          audio_input_mime: mimeType,
          voice_id: profile?.preferredVoiceId || user?.preferredVoiceId,
          tts_model: (profile?.preferredTtsModel || user?.preferredTtsModel || 'v2_5_turbo') as any,
        },
      };

      let response: SendMessageResponse;
      if (chatResponseMode === 'stream') {
        resetStreamDrainer();
        setAssistantTranscript('');
        response = await chatAPI.streamMessage(sendPayload, (event) => {
          if (event.event === 'token') {
            streamPendingRef.current += event.data;
          }
        });
        queryClient.invalidateQueries({ queryKey: ['messages', targetConversationId] });
        queryClient.invalidateQueries({ queryKey: ['conversations'] });
      } else {
        response = await sendMessageMutation.mutateAsync(sendPayload);
      }

      if (response.phq9_state !== undefined) {
        phq9StateByConversationRef.current[targetConversationId] = response.phq9_state;
      }
      if (response.cbt_state !== undefined) {
        cbtStateByConversationRef.current[targetConversationId] = response.cbt_state;
      }

      const transcript = response.voice?.transcript || response.userMessage?.content || '';
      const assistantMessage: Message | undefined = response.assistantMessage;
      const assistantText = assistantMessage?.content || response.reply || '';
      const spokenAssistantText = response.voice?.speech_response || assistantText;
      setUserTranscript(transcript);
      setAssistantTranscript('');
      setStatus('processing');
      if (transcript) {
        await new Promise((resolve) => setTimeout(resolve, USER_TRANSCRIPT_PREVIEW_MS));
      }
      resetStreamDrainer();
      streamPendingRef.current = assistantText;
      startStreamDrainer();
      setStatus('speaking');

      const audioSource = response.voice?.audio_output_base64
        ? dataUrlFromBase64(response.voice.audio_output_base64, response.voice.audio_output_format || 'mpeg')
        : response.voice?.audio_output_url;

      if (audioSource) {
        try {
          await playVoiceSource(audioSource);
        } catch (playbackError) {
          console.warn('Voice room audio playback was blocked by the browser.', playbackError);
          if (spokenAssistantText) {
            speakWithBrowser(spokenAssistantText, user?.preferredLanguage === 'en' ? 'en-US' : 'id-ID');
            await new Promise((resolve) =>
              setTimeout(resolve, Math.min(5200, Math.max(2200, spokenAssistantText.length * 42)))
            );
          }
        }
      } else if (spokenAssistantText) {
        speakWithBrowser(spokenAssistantText, user?.preferredLanguage === 'en' ? 'en-US' : 'id-ID');
        await new Promise((resolve) => setTimeout(resolve, Math.min(5200, Math.max(2200, spokenAssistantText.length * 42))));
      }
      await new Promise((resolve) => setTimeout(resolve, AI_TAIL_PADDING_MS));
    } catch (voiceError) {
      console.error('Failed to run voice room interaction:', voiceError);
      setError(t('voiceFailed'));
    } finally {
      setIsRecording(false);
      if (conversationActiveRef.current) {
        clearSubtitleLater();
        if (cooldownTimerRef.current) {
          clearTimeout(cooldownTimerRef.current);
        }
        cooldownTimerRef.current = setTimeout(() => {
          cooldownTimerRef.current = null;
          if (!conversationActiveRef.current) return;
          listeningLockedRef.current = false;
          setStatus('listening');
          void startListeningCycle();
        }, POST_AI_LISTEN_DELAY_MS);
      } else {
        listeningLockedRef.current = false;
        setStatus('idle');
        clearSubtitleLater();
      }
    }
  };

  const startConversation = async () => {
    if (!userId) {
      router.push('/auth?next=/voice-room');
      return;
    }
    if (conversationActiveRef.current) return;
    const targetConversationId = await ensureConversation();
    if (!targetConversationId) return;
    lockedConversationIdRef.current = targetConversationId;
    setLockedConversationId(targetConversationId);
    unlockAudioPlayback();
    setConversationActive(true);
    conversationActiveRef.current = true;
    await startListeningCycle();
  };

  const stopConversation = () => {
    setConversationActive(false);
    conversationActiveRef.current = false;
    lockedConversationIdRef.current = null;
    setLockedConversationId(null);
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }
    resetStreamDrainer();
    listeningLockedRef.current = false;
    stopCurrentRecording(false);
    stopVoicePlayback();
    setStatus('idle');
    setIsRecording(false);
    clearSubtitleLater(1100);
  };

  const toggleVoiceRecording = () => {
    if (conversationActiveRef.current) {
      stopConversation();
      return;
    }
    void startConversation();
  };

  useEffect(() => {
    return () => {
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current);
      }
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
      }
      resetStreamDrainer();
      listeningLockedRef.current = false;
      conversationActiveRef.current = false;
      lockedConversationIdRef.current = null;
      stopCurrentRecording(false);
      stopVoicePlayback();
    };
  }, []);

  if (isInitialized && !isAuthenticated) {
    return null;
  }

  return (
    <VoiceRoom
      status={status}
      transcript={userTranscript}
      error={error}
      isRecording={isRecording}
      disabled={false}
      conversationActive={conversationActive}
      audioLevel={status === 'listening' ? voiceLevel : undefined}
      hoverHint={
        conversationActive
          ? status === 'listening'
            ? t('voiceRoomListeningHint')
            : status === 'processing'
              ? t('voiceRoomProcessingHint')
              : status === 'speaking'
                ? t('voiceRoomSpeakingHint')
                : t('voiceRoomStopHint')
          : t('voiceRoomStartHint')
      }
      userTranscript={userTranscript}
      assistantTranscript={assistantTranscript}
      sessionMessages={sessionMessages}
      showMiniSession={showMiniSession}
      onToggleMiniSession={() => setShowMiniSession((value) => !value)}
      conversations={conversations}
      selectedConversationId={conversationId}
      onSelectConversation={(id) => {
        if (conversationActiveRef.current) {
          stopConversation();
        }
        lockedConversationIdRef.current = null;
        setLockedConversationId(null);
        setConversationId(id);
        setShowMiniSession(false);
        setUserTranscript('');
        setAssistantTranscript('');
        setError(null);
      }}
      onToggleVoice={toggleVoiceRecording}
    />
  );
}

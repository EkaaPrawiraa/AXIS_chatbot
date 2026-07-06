'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSearchParams, useRouter } from 'next/navigation';
import { AppShell } from '@/components/layout';
import { ChatLayout, VoiceInteractionStatus } from '@/components/chat';
import { useChatMessages, useConversations, useCreateConversation } from '@/hooks';
import { useSessionStore, useChatStore, usePreferencesStore } from '@/stores';
import { Conversation, Message, ID } from '@/models';
import { Button } from '@/components/ui/button';
import { MessageSquare, Plus } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { blobToBase64, createAudioPlayer, dataUrlFromBase64, playAudioSource, speakWithBrowser, stopActiveAudio } from '@/lib/audio';
import { voiceAPI } from '@/lib/api/voice';
import { chatAPI } from '@/lib/api/chat';
import { useT } from '@/lib/i18n';

type StreamDraftState = {
  conversationId: ID;
  pending: string;
  revealed: string;
  timer: ReturnType<typeof setInterval> | null;
};

type Phq9MessageMetadata = NonNullable<NonNullable<Message['metadata']>['phq9']>;

function phq9MetadataFromState(phq9State?: Record<string, unknown>): Message['metadata'] | undefined {
  if (!phq9State) return undefined;
  const phase = typeof phq9State.phase === 'string' ? phq9State.phase : '';
  if (!phase || phase === 'idle' || phase === 'offer_pending') return undefined;

  const language = typeof phq9State.language === 'string' ? phq9State.language : 'id';
  const active = phase === 'offered' || phase === 'in_progress' || phase === 'awaiting_clar';
  const activeItemRaw = phq9State.active_item;
  const activeItem =
    typeof activeItemRaw === 'number'
      ? activeItemRaw
      : typeof activeItemRaw === 'string'
        ? Number.parseInt(activeItemRaw, 10)
        : 1;

  const phq9: Phq9MessageMetadata = {
    active,
    phase: phase as Phq9MessageMetadata['phase'],
    language,
    allow_free_text: true,
  };

  if (phase === 'offered') {
    phq9.options =
      language === 'en'
        ? [
            { score: null, label: 'Accept' },
            { score: null, label: 'Decline' },
          ]
        : [
            { score: null, label: 'Mulai' },
            { score: null, label: 'Lewati' },
          ];
    phq9.progress = { current: 0, total: 9 };
  } else if (phase === 'in_progress' || phase === 'awaiting_clar') {
    const itemId = Number.isFinite(activeItem) && activeItem > 0 ? activeItem : 1;
    phq9.item_id = itemId;
    phq9.options =
      language === 'en'
        ? [
            { score: 0, label: 'Not at all' },
            { score: 1, label: 'Several days' },
            { score: 2, label: 'More than half the days' },
            { score: 3, label: 'Nearly every day' },
          ]
        : [
            { score: 0, label: 'Tidak sama sekali' },
            { score: 1, label: 'Beberapa hari' },
            { score: 2, label: 'Lebih dari setengah hari' },
            { score: 3, label: 'Hampir setiap hari' },
          ];
    phq9.progress = { current: itemId, total: 9 };
  } else {
    phq9.active = false;
    phq9.progress = { current: 9, total: 9 };
  }

  return { phq9 };
}

function phq9MetadataFromContent(content: string): Message['metadata'] | undefined {
  const normalized = content.toLowerCase();
  const questionMatch = content.match(/pertanyaan\s+(\d+)\s+dari\s+9/i);
  const hasAnswerScale =
    normalized.includes('tidak sama sekali') &&
    normalized.includes('beberapa hari') &&
    normalized.includes('hampir setiap hari');

  if (questionMatch && hasAnswerScale) {
    const itemId = Number.parseInt(questionMatch[1], 10);
    const safeItemId = Number.isFinite(itemId) && itemId > 0 ? itemId : 1;
    return {
      phq9: {
        active: true,
        phase: 'in_progress',
        language: 'id',
        allow_free_text: true,
        item_id: safeItemId,
        progress: { current: safeItemId, total: 9 },
        options: [
          { score: 0, label: 'Tidak sama sekali' },
          { score: 1, label: 'Beberapa hari' },
          { score: 2, label: 'Lebih dari setengah hari' },
          { score: 3, label: 'Hampir setiap hari' },
        ],
      },
    };
  }

  const mentionsPhq = normalized.includes('phq-9') || normalized.includes('tes mood') || normalized.includes('cek mood');
  const looksLikeOffer =
    mentionsPhq &&
    (normalized.includes('mulai') || normalized.includes('mau coba') || normalized.includes('lewati'));

  if (looksLikeOffer) {
    return {
      phq9: {
        active: true,
        phase: 'offered',
        language: 'id',
        allow_free_text: true,
        progress: { current: 0, total: 9 },
        options: [
          { score: null, label: 'Mulai' },
          { score: null, label: 'Lewati' },
        ],
      },
    };
  }

  return undefined;
}

function withResponseMetadata(message: Message, response: { phq9_state?: Record<string, unknown>; safety_flag?: string; crisis_tier?: string }) {
  const phq9Metadata = message.metadata?.phq9
    ? undefined
    : phq9MetadataFromState(response.phq9_state) || phq9MetadataFromContent(message.content || '');
  const nextMetadata = {
    ...(response.safety_flag ? { safetyFlag: response.safety_flag } : {}),
    ...(response.crisis_tier ? { crisisTier: response.crisis_tier } : {}),
    ...(message.metadata || {}),
    ...(phq9Metadata || {}),
  };
  return Object.keys(nextMetadata).length > 0 ? { ...message, metadata: nextMetadata } : message;
}

function withOnlyCurrentPhqPrompt(messages: Message[], currentSessionBusy: boolean): Message[] {
  const lastUserIndex = messages.reduce((latest, message, index) => (message.role === 'user' ? index : latest), -1);
  const activePhqIndex = currentSessionBusy
    ? -1
    : messages.reduce((latest, message, index) => {
        if (index <= lastUserIndex) return latest;
        if (message.role !== 'assistant' || !message.metadata?.phq9?.active) return latest;
        return index;
      }, -1);

  return messages.map((message, index) => {
    if (!message.metadata?.phq9?.active || index === activePhqIndex) return message;
    return {
      ...message,
      metadata: {
        ...message.metadata,
        phq9: {
          ...message.metadata.phq9,
          active: false,
        },
      },
    };
  });
}

function ChatContent() {
  const t = useT();
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const conversationId = searchParams.get('id') as ID | null;

  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const isInitialized = useSessionStore((state) => state.isInitialized);
  const activeConversationId = useChatStore((state) => state.activeConversationId);
  const setActiveConversationId = useChatStore((state) => state.setActiveConversationId);
  const setIsStreaming = useChatStore((state) => state.setIsStreaming);
  const chatResponseMode = usePreferencesStore((state) => state.chatResponseMode);
  const activeUserId = isAuthenticated ? userId : null;
  const currentConversationId = conversationId || activeConversationId;

  const { data: messages = [], isLoading: isLoadingMessages } = useChatMessages(currentConversationId);
  const { data: conversations = [], isLoading: isLoadingConversations } = useConversations(activeUserId);
  const createConversationMutation = useCreateConversation();
  const preferredResponseModel = profile?.preferredResponseModel || user?.preferredResponseModel;

  const [optimisticMessagesByConversation, setOptimisticMessagesByConversation] = useState<Record<string, Message[]>>({});
  const [inFlightByConversation, setInFlightByConversation] = useState<Record<string, number>>({});
  const [voiceStatus, setVoiceStatus] = useState<VoiceInteractionStatus>('idle');
  const phq9StateByConversationRef = useRef<Record<string, Record<string, unknown> | undefined>>({});
  const cbtStateByConversationRef = useRef<Record<string, Record<string, unknown> | undefined>>({});
  const awaitingMessageIdByConversationRef = useRef<Record<string, string | undefined>>({});
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);
  const [isComposingNewConversation, setIsComposingNewConversation] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const voiceChunksRef = useRef<BlobPart[]>([]);
  const voiceStreamRef = useRef<MediaStream | null>(null);
  const currentAudioStopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (isInitialized && !isAuthenticated) {
      router.replace('/auth?next=/chat');
    }
  }, [isAuthenticated, isInitialized, router]);
  const streamDraftsRef = useRef<Record<string, StreamDraftState>>({});
  const activeInFlightCount = currentConversationId ? inFlightByConversation[currentConversationId] || 0 : 0;
  const currentSessionBusy = activeInFlightCount > 0;

  const setConversationOptimisticMessages = (targetConversationId: ID, nextMessages: Message[]) => {
    setOptimisticMessagesByConversation((current) => ({
      ...current,
      [targetConversationId]: nextMessages,
    }));
  };

  const clearConversationOptimisticMessages = (targetConversationId: ID) => {
    setOptimisticMessagesByConversation((current) => {
      const { [targetConversationId]: _removed, ...rest } = current;
      return rest;
    });
  };

  const updateConversationOptimisticMessage = (
    targetConversationId: ID,
    messageId: string,
    updater: (message: Message) => Message
  ) => {
    setOptimisticMessagesByConversation((current) => ({
      ...current,
      [targetConversationId]: (current[targetConversationId] || []).map((message) =>
        message.id === messageId ? updater(message) : message
      ),
    }));
  };

  const incrementInFlight = (targetConversationId: ID) => {
    setInFlightByConversation((current) => ({
      ...current,
      [targetConversationId]: (current[targetConversationId] || 0) + 1,
    }));
  };

  const decrementInFlight = (targetConversationId: ID) => {
    setInFlightByConversation((current) => {
      const nextCount = Math.max((current[targetConversationId] || 1) - 1, 0);
      if (nextCount === 0) {
        const { [targetConversationId]: _removed, ...rest } = current;
        return rest;
      }
      return { ...current, [targetConversationId]: nextCount };
    });
  };

  const startStreamDrainer = (draftId: string) => {
    const draft = streamDraftsRef.current[draftId];
    if (!draft || draft.timer) return;
    draft.timer = setInterval(() => {
      const activeDraft = streamDraftsRef.current[draftId];
      if (!activeDraft) return;
      const target = activeDraft.pending;
      const current = activeDraft.revealed;
      if (current.length >= target.length) return;
      const remaining = target.length - current.length;
      const step = remaining > 120 ? 8 : remaining > 48 ? 5 : remaining > 16 ? 3 : 1;
      const next = target.slice(0, current.length + step);
      activeDraft.revealed = next;
      updateConversationOptimisticMessage(activeDraft.conversationId, draftId, (message) => ({
        ...message,
        content: next,
        updatedAt: Date.now(),
      }));
    }, 26);
  };

  const appendStreamToken = (draftId: string, token: string) => {
    const draft = streamDraftsRef.current[draftId];
    if (!draft) return;
    draft.pending += token;
    startStreamDrainer(draftId);
  };

  const flushStreamDrainer = (draftId: string) => {
    const draft = streamDraftsRef.current[draftId];
    if (!draft) return;
    draft.revealed = draft.pending;
    updateConversationOptimisticMessage(draft.conversationId, draftId, (message) => ({
      ...message,
      content: draft.pending,
      updatedAt: Date.now(),
    }));
  };

  const resetStreamDrainer = (draftId: string) => {
    const draft = streamDraftsRef.current[draftId];
    if (draft?.timer) {
      clearInterval(draft.timer);
    }
    delete streamDraftsRef.current[draftId];
  };

  useEffect(() => {
    if (conversationId && conversationId !== activeConversationId) {
      setActiveConversationId(conversationId);
    }
  }, [conversationId, activeConversationId, setActiveConversationId]);

  useEffect(() => {
    if (conversationId || activeConversationId) {
      setIsComposingNewConversation(false);
    }
  }, [conversationId, activeConversationId]);

  useEffect(() => {
    if (!currentConversationId) return;
    const awaitingId = awaitingMessageIdByConversationRef.current[currentConversationId];
    if (!awaitingId) return;
    if (messages.some((m) => m.id === awaitingId)) {
      clearConversationOptimisticMessages(currentConversationId);
      delete awaitingMessageIdByConversationRef.current[currentConversationId];
      return;
    }
    if (awaitingId.startsWith('assistant-') || awaitingId.startsWith('voice-')) {
      const timer = setTimeout(() => {
        clearConversationOptimisticMessages(currentConversationId);
        delete awaitingMessageIdByConversationRef.current[currentConversationId];
      }, 5_000);
      return () => clearTimeout(timer);
    }
  }, [messages, currentConversationId]);

  useEffect(() => {
    const totalInFlight = Object.values(inFlightByConversation).reduce((sum, count) => sum + count, 0);
    setIsStreaming(totalInFlight > 0);
  }, [inFlightByConversation, setIsStreaming]);

  const handleSendMessage = async (content: string) => {
    if (!userId) {
      router.push('/auth?next=/chat');
      return;
    }

    let targetConversationId = conversationId || activeConversationId;

    try {
      setVoiceError(null);

      if (!targetConversationId) {
        const conversation = await createConversationMutation.mutateAsync({
          userId,
          title: content.slice(0, 60) || t('newConversation'),
        });
        targetConversationId = conversation.id;
        setActiveConversationId(conversation.id);
        router.replace(`/chat?id=${conversation.id}`);
        phq9StateByConversationRef.current[conversation.id] = undefined;
        cbtStateByConversationRef.current[conversation.id] = undefined;
      }
      incrementInFlight(targetConversationId);

      const userMessage: Message = {
        id: 'temp-' + Date.now(),
        conversationId: targetConversationId,
        role: 'user',
        content,
        status: 'sending',
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      setConversationOptimisticMessages(targetConversationId, [userMessage]);

      if (chatResponseMode === 'stream') {
        const assistantDraftId = 'assistant-stream-' + Date.now();
        const assistantDraft: Message = {
          id: assistantDraftId,
          conversationId: targetConversationId,
          role: 'assistant',
          content: '',
          status: 'sending',
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        setConversationOptimisticMessages(targetConversationId, [userMessage, assistantDraft]);
        streamDraftsRef.current[assistantDraftId] = {
          conversationId: targetConversationId,
          pending: '',
          revealed: '',
          timer: null,
        };

        const response = await chatAPI.streamMessage(
          {
            conversationId: targetConversationId,
            content,
            userId,
            language_pref: user?.preferredLanguage || 'id',
            preferred_response_model: preferredResponseModel,
            phq9_state: phq9StateByConversationRef.current[targetConversationId],
            cbt_state: cbtStateByConversationRef.current[targetConversationId],
          },
          (event) => {
            if (event.event === 'token') {
              appendStreamToken(assistantDraftId, event.data);
            }
          }
        );

        if (response.phq9_state !== undefined) phq9StateByConversationRef.current[targetConversationId] = response.phq9_state;
        if (response.cbt_state !== undefined) cbtStateByConversationRef.current[targetConversationId] = response.cbt_state;

        const assistantMsg: Message = withResponseMetadata(response.assistantMessage || {
          id: response.messageId || 'assistant-' + Date.now(),
          conversationId: targetConversationId,
          role: 'assistant',
          content: response.reply,
          status: 'sent',
          metadata:
            response.safety_flag || response.crisis_tier
              ? {
                  ...(response.safety_flag ? { safetyFlag: response.safety_flag } : {}),
                  ...(response.crisis_tier ? { crisisTier: response.crisis_tier } : {}),
                }
              : undefined,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }, response);
        const draft = streamDraftsRef.current[assistantDraftId];
        if (draft) {
          draft.pending = assistantMsg.content || response.reply || draft.pending;
          flushStreamDrainer(assistantDraftId);
        }
        setConversationOptimisticMessages(targetConversationId, [response.userMessage || userMessage, assistantMsg]);
        resetStreamDrainer(assistantDraftId);
        awaitingMessageIdByConversationRef.current[targetConversationId] = assistantMsg.id;
        queryClient.invalidateQueries({ queryKey: ['messages', targetConversationId] });
        queryClient.invalidateQueries({ queryKey: ['conversations'] });
        return;
      }

      const response = await chatAPI.sendMessage({
        conversationId: targetConversationId,
        content,
        userId,
        language_pref: user?.preferredLanguage || 'id',
        preferred_response_model: preferredResponseModel,
        phq9_state: phq9StateByConversationRef.current[targetConversationId],
        cbt_state: cbtStateByConversationRef.current[targetConversationId],
      });

      if (response.phq9_state !== undefined) phq9StateByConversationRef.current[targetConversationId] = response.phq9_state;
      if (response.cbt_state !== undefined) cbtStateByConversationRef.current[targetConversationId] = response.cbt_state;

      const assistantMsg: Message = withResponseMetadata(response.assistantMessage || {
        id: response.messageId || 'assistant-' + Date.now(),
        conversationId: targetConversationId,
        role: 'assistant',
        content: response.reply,
        status: 'sent',
        metadata:
          response.safety_flag || response.crisis_tier
            ? {
                ...(response.safety_flag ? { safetyFlag: response.safety_flag } : {}),
                ...(response.crisis_tier ? { crisisTier: response.crisis_tier } : {}),
              }
            : undefined,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      }, response);
      setConversationOptimisticMessages(targetConversationId, [response.userMessage || userMessage, assistantMsg]);
      awaitingMessageIdByConversationRef.current[targetConversationId] = assistantMsg.id;
      queryClient.invalidateQueries({ queryKey: ['messages', targetConversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    } catch (error) {
      console.error('Failed to send message:', error);
      if (targetConversationId) {
        const failedConversationId = targetConversationId;
        setOptimisticMessagesByConversation((current) => ({
          ...current,
          [failedConversationId]: (current[failedConversationId] || []).map((message: Message) =>
            message.role === 'user' ? { ...message, status: 'failed' } : message
          ),
        }));
      }
    } finally {
      if (targetConversationId) decrementInFlight(targetConversationId);
    }
  };

  const handleSendVoice = async (audio: Blob, mimeType: string) => {
    if (!userId) {
      router.push('/auth?next=/chat');
      return;
    }

    let targetConversationId = conversationId || activeConversationId;

    try {
      if (!targetConversationId) {
        const conversation = await createConversationMutation.mutateAsync({
          userId,
          title: t('newConversation'),
        });
        targetConversationId = conversation.id;
        setActiveConversationId(conversation.id);
        router.replace(`/chat?id=${conversation.id}`);
        phq9StateByConversationRef.current[conversation.id] = undefined;
        cbtStateByConversationRef.current[conversation.id] = undefined;
      }
      incrementInFlight(targetConversationId);

      const audioBase64 = await blobToBase64(audio);
      const pendingMessage: Message = {
        id: 'voice-temp-' + Date.now(),
        conversationId: targetConversationId,
        role: 'user',
        content: t('voiceProcessingMessage'),
        status: 'sending',
        metadata: { audioOutputUrl: URL.createObjectURL(audio), audioOutputFormat: mimeType },
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      setConversationOptimisticMessages(targetConversationId, [pendingMessage]);

      const response = await chatAPI.sendMessage({
        conversationId: targetConversationId,
        content: '',
        userId,
        language_pref: user?.preferredLanguage || 'id',
        preferred_response_model: preferredResponseModel,
        phq9_state: phq9StateByConversationRef.current[targetConversationId],
        cbt_state: cbtStateByConversationRef.current[targetConversationId],
        voice: {
          output_modality: 'both',
          audio_input_base64: audioBase64,
          audio_input_mime: mimeType,
          voice_id: profile?.preferredVoiceId || user?.preferredVoiceId,
          tts_model: (profile?.preferredTtsModel || user?.preferredTtsModel || 'v2_5_turbo') as any,
        },
      });

      if (response.phq9_state !== undefined) phq9StateByConversationRef.current[targetConversationId] = response.phq9_state;
      if (response.cbt_state !== undefined) cbtStateByConversationRef.current[targetConversationId] = response.cbt_state;

      const transcript = response.voice?.transcript || response.userMessage?.content || t('recordVoiceMessage');
      setVoiceTranscript(transcript);
      const voiceMetadata = response.voice
        ? {
            transcript: response.voice.transcript,
            audioOutputBase64: response.voice.audio_output_base64,
            audioOutputUrl: response.voice.audio_output_url,
            audioOutputFormat: response.voice.audio_output_format,
            voice: response.voice,
          }
        : undefined;

      const assistantMessage: Message =
        response.assistantMessage || {
          id: response.messageId || 'assistant-' + Date.now(),
          conversationId: targetConversationId,
          role: 'assistant',
          content: response.reply,
          status: 'sent',
          metadata: voiceMetadata,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };

      const voiceAssistantMsg: Message = withResponseMetadata({
        ...assistantMessage,
        metadata: { ...(assistantMessage.metadata || {}), ...voiceMetadata },
      }, response);
      setConversationOptimisticMessages(targetConversationId, [
        {
          ...(response.userMessage || pendingMessage),
          content: transcript,
          status: 'sent',
          metadata: { ...(response.userMessage?.metadata || {}), transcript },
        },
        voiceAssistantMsg,
      ]);
      awaitingMessageIdByConversationRef.current[targetConversationId] = voiceAssistantMsg.id;
      queryClient.invalidateQueries({ queryKey: ['messages', targetConversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });

      if (response.voice?.audio_output_base64) {
        setVoiceStatus('speaking');
        await playAudioSource(
          dataUrlFromBase64(response.voice.audio_output_base64, response.voice.audio_output_format || 'mpeg')
        );
      } else if (response.voice?.audio_output_url) {
        setVoiceStatus('speaking');
        await playAudioSource(response.voice.audio_output_url);
      }
    } catch (error) {
      console.error('Failed to send voice message:', error);
      setVoiceError(t('voiceFailed'));
      if (targetConversationId) {
        const failedConversationId = targetConversationId;
        setOptimisticMessagesByConversation((current) => ({
          ...current,
          [failedConversationId]: (current[failedConversationId] || []).map((message: Message) =>
            message.role === 'user' ? { ...message, status: 'failed' } : message
          ),
        }));
      }
    } finally {
      if (targetConversationId) decrementInFlight(targetConversationId);
      setVoiceStatus('idle');
    }
  };

  const startVoiceRecording = async () => {
    if (!userId) {
      router.push('/auth?next=/chat');
      return;
    }
    if (currentSessionBusy || isVoiceRecording) return;

    try {
      setVoiceError(null);
      setVoiceTranscript('');
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

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) voiceChunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        voiceStreamRef.current = null;
        const blob = new Blob(voiceChunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' });
        voiceChunksRef.current = [];
        if (blob.size > 0) {
          setVoiceStatus('processing');
          void handleSendVoice(blob, blob.type || mimeType || 'audio/webm');
        } else {
          setVoiceStatus('idle');
        }
      };

      recorder.start();
      setIsVoiceRecording(true);
      setVoiceStatus('listening');
    } catch (error) {
      console.error('Failed to start voice recording:', error);
      setVoiceError(t('voiceFailed'));
      setIsVoiceRecording(false);
      setVoiceStatus('idle');
    }
  };

  const stopVoiceRecording = () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
    voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
    voiceStreamRef.current = null;
    setIsVoiceRecording(false);
  };

  const toggleVoiceRecording = () => {
    if (isVoiceRecording) {
      stopVoiceRecording();
      return;
    }
    void startVoiceRecording();
  };

  useEffect(() => {
    return () => {
      Object.values(streamDraftsRef.current).forEach((draft) => {
        if (draft.timer) clearInterval(draft.timer);
      });
      streamDraftsRef.current = {};
      voiceStreamRef.current?.getTracks().forEach((track) => track.stop());
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.stop();
      }
    };
  }, []);

  const handleStopMessage = () => {
    currentAudioStopRef.current?.();
    currentAudioStopRef.current = null;
    stopActiveAudio();
  };

  const handleCopyMessage = async (content: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(content);
      return;
    }
    if (typeof document === 'undefined') return;
    const textarea = document.createElement('textarea');
    textarea.value = content;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  };

  const handlePlayMessage = async (message: Message, onStarted: () => void): Promise<void> => {
    handleStopMessage();

    const audioBase64 = message.metadata?.audioOutputBase64 || message.metadata?.voice?.audio_output_base64;
    const audioUrl = message.metadata?.audioOutputUrl || message.metadata?.voice?.audio_output_url;
    const audioFormat = message.metadata?.audioOutputFormat || message.metadata?.voice?.audio_output_format || 'mpeg';

    const playSrc = (src: string) => {
      const player = createAudioPlayer(src, onStarted);
      currentAudioStopRef.current = player.stop;
      return player.done.finally(() => {
        currentAudioStopRef.current = null;
      });
    };

    if (audioBase64) {
      return playSrc(dataUrlFromBase64(audioBase64, audioFormat));
    }
    if (audioUrl) {
      return playSrc(audioUrl);
    }

    try {
      const synthesized = await voiceAPI.synthesize({
        text: message.content,
        voice_id: profile?.preferredVoiceId || user?.preferredVoiceId,
        tts_model: (profile?.preferredTtsModel || user?.preferredTtsModel || 'v2_5_turbo') as any,
        language_pref: user?.preferredLanguage || 'id',
      });
      if (synthesized.audio_output_base64) {
        return playSrc(dataUrlFromBase64(synthesized.audio_output_base64, synthesized.audio_output_format || 'mpeg'));
      }
      if (synthesized.audio_output_url) {
        return playSrc(synthesized.audio_output_url);
      }
    } catch (error) {
      console.warn('Backend TTS endpoint unavailable, using browser speech synthesis fallback.', error);
    }

    onStarted();
    speakWithBrowser(message.content, user?.preferredLanguage === 'en' ? 'en-US' : 'id-ID');
  };

  const currentOptimisticMessages = currentConversationId
    ? optimisticMessagesByConversation[currentConversationId] || []
    : [];
  const optimisticMessagesById = new Map(currentOptimisticMessages.map((message) => [message.id, message]));
  const mergedMessages = messages.map((message) => {
    const optimistic = optimisticMessagesById.get(message.id);
    const inferredMetadata = message.role === 'assistant' ? phq9MetadataFromContent(message.content || '') : undefined;
    if (!optimistic?.metadata && !inferredMetadata) return message;
    return {
      ...message,
      metadata: {
        ...(message.metadata || {}),
        ...(inferredMetadata || {}),
        ...(optimistic?.metadata || {}),
      },
    };
  });
  const messageIds = new Set(mergedMessages.map((message) => message.id));
  const pendingMessages = currentOptimisticMessages.filter((message) => !messageIds.has(message.id));
  const displayMessages = withOnlyCurrentPhqPrompt(
    pendingMessages.length > 0 ? [...mergedMessages, ...pendingMessages] : mergedMessages,
    currentSessionBusy
  );
  const showSessionPicker =
    !conversationId &&
    !activeConversationId &&
    !isComposingNewConversation &&
    !isLoadingConversations &&
    conversations.length > 0;
  const showComposer =
    Boolean(currentConversationId) ||
    isComposingNewConversation ||
    (!isLoadingConversations && conversations.length === 0);

  if (isInitialized && !isAuthenticated) {
    return null;
  }

  return (
    <ChatLayout
      messages={displayMessages}
      isLoading={isLoadingMessages}
      isStreaming={currentSessionBusy}
      chatResponseMode={chatResponseMode}
      onSendMessage={handleSendMessage}
      onVoiceStateChange={setVoiceStatus}
      onToggleVoice={toggleVoiceRecording}
      voiceEnabled
      voiceStatus={voiceStatus}
      voiceTranscript={voiceTranscript}
      voiceError={voiceError}
      isVoiceRecording={isVoiceRecording}
      onCopyMessage={(content) => void handleCopyMessage(content)}
      onPlayMessage={handlePlayMessage}
      onStopMessage={handleStopMessage}
      showComposer={showComposer}
      emptyContent={
        showSessionPicker ? (
          <SessionStartPanel
            conversations={conversations}
            isLoading={isLoadingConversations}
            onNewChat={() => {
              setActiveConversationId(null);
              setIsComposingNewConversation(true);
              router.push('/chat');
            }}
            onOpen={(id) => {
              setActiveConversationId(id);
              router.push(`/chat?id=${id}`);
            }}
          />
        ) : undefined
      }
    />
  );
}

function SessionStartPanel({
  conversations,
  isLoading,
  onNewChat,
  onOpen,
}: {
  conversations: Conversation[];
  isLoading: boolean;
  onNewChat: () => void;
  onOpen: (id: ID) => void;
}) {
  const t = useT();
  const recent = conversations.slice(0, 6);

  return (
    <div className="mx-auto flex h-full w-full max-w-5xl flex-col justify-center py-6">
      <div className="mb-6 flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          {/* <p className="axis-eyebrow mb-4">{t('companionChat')}</p> */}
          <h2 className="max-w-2xl text-4xl font-semibold leading-[0.98] tracking-[-0.055em] sm:text-5xl">
            {t('sessions')}
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{t('chooseSession')}</p>
        </div>
        <Button onClick={onNewChat} className="rounded-xl">
          <Plus className="mr-2 h-4 w-4" />
          {t('newChat')}
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} className="rounded-[1.25rem] p-4">
              <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
              <div className="mt-3 h-3 w-1/3 animate-pulse rounded bg-muted" />
            </Card>
          ))}
        </div>
      ) : recent.length === 0 ? (
        <Card className="rounded-[1.35rem] border-dashed p-8 text-center">
          <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl border border-border bg-muted/45 text-primary">
            <MessageSquare className="h-5 w-5" />
          </div>
          <h3 className="font-semibold">{t('noSessions')}</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {t('noSessionsDescription')}
          </p>
        </Card>
      ) : (
        <div className="grid w-full min-w-0 gap-3">
          {recent.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              onClick={() => onOpen(conversation.id)}
              className="block w-full min-w-0 text-left"
            >
              <Card className="w-full min-w-0 overflow-hidden rounded-[1.25rem] p-4 transition-[border-color,box-shadow,transform] duration-300 hover:-translate-y-0.5 hover:border-ring/35 hover:shadow-[var(--axis-shadow)]">
                <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                  <div className="min-w-0 overflow-hidden">
                    <h3 className="max-w-full truncate text-sm font-semibold leading-5 sm:text-base">
                      {conversation.title || t('newConversation')}
                    </h3>
                    <p className="mt-1 line-clamp-2 max-w-full break-words text-sm leading-5 text-muted-foreground [overflow-wrap:anywhere]">
                      {conversation.preview || t('messages', conversation.messageCount || 0)}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full border border-border bg-muted/35 px-2 py-1 font-mono text-[10px] text-muted-foreground">
                    {conversation.messageCount || 0}
                  </span>
                </div>
              </Card>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <AppShell>
      <Suspense
        fallback={
          <div className="flex h-full items-center justify-center px-6">
            <div className="axis-panel w-full max-w-md rounded-[1.35rem] p-6">
              <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
              <div className="mt-3 h-3 w-full animate-pulse rounded bg-muted" />
              <div className="mt-2 h-3 w-4/5 animate-pulse rounded bg-muted" />
            </div>
          </div>
        }
      >
        <ChatContent />
      </Suspense>
    </AppShell>
  );
}

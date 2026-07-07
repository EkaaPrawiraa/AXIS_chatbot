'use client';

import { Loader2 } from '@/lib/assets';
import { useRouter, useSearchParams } from 'next/navigation';
import { Fragment, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { AuthRequired } from '@/components/session';
import { V2Shell } from '@/components/v2/V2Shell';
import { AssistantBubble } from '@/components/v2/chat/bubbles/AssistantBubble';
import { ChatComposer } from '@/components/v2/chat/composer/ChatComposer';
import { ChatHeader } from '@/components/v2/chat/header/ChatHeader';
import { formatChatDateDivider, isDifferentCalendarDay } from '@/components/v2/chat/utils/format';
import { HotlineWarningCard } from '@/components/v2/chat/cards/HotlineWarningCard';
import { SessionListView } from '@/components/v2/chat/SessionList';
import { UserBubble } from '@/components/v2/chat/bubbles/UserBubble';
import { chatAPI } from '@/lib/api/chat';
import { voiceAPI } from '@/lib/api/voice';
import { animationClasses, motionStyleVars } from '@/lib/animations';
import { chatSounds } from '@/lib/sounds';
import { createAudioPlayer, dataUrlFromBase64, primeAudioElement } from '@/lib/audio';
import { stripCrisisResourceBlock } from '@/lib/crisisResources';
import { friendlyErrorMessage } from '@/lib/errorMessages';
import { useKeyboardInset } from '@/lib/useVisualViewportHeight';
import { type Conversation, type Message } from '@/models';
import { usePreferencesStore } from '@/stores/preferences';
import { useSessionStore } from '@/stores';
import { useMessageLimitStore } from '@/stores/messageLimit';
import { useUIStore } from '@/stores/ui';

import { chatRoomStyles } from '@/lib/styles/chatRoom';

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const keyboardInset = useKeyboardInset();
  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const messageLimit = useMessageLimitStore();
  const addToast = useUIStore((state) => state.addToast);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(searchParams.get('conversationId'));
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [answeredPhqMessageIds, setAnsweredPhqMessageIds] = useState<Set<string>>(() => new Set());
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [regeneratingMessageId, setRegeneratingMessageId] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const phq9StateByConversationRef = useRef<Record<string, Record<string, unknown> | undefined>>({});
  const cbtStateByConversationRef = useRef<Record<string, Record<string, unknown> | undefined>>({});
  const chatResponseMode = usePreferencesStore((state) => state.chatResponseMode);
  const name = user?.displayName || 'teman';

  const filteredConversations = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return conversations;
    return conversations.filter((conversation) => {
      const title = conversation.title || 'Cerita baru';
      const preview = conversation.preview || '';
      return `${title} ${preview}`.toLowerCase().includes(query);
    });
  }, [conversations, searchQuery]);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    chatAPI.getConversations(userId).then((items) => {
      if (cancelled) return;
      setConversations(items);
    });
    return () => {
      cancelled = true;
    };
  }, [conversationId, router, userId]);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    chatAPI.getMessages(conversationId, 1, 100, userId ?? undefined).then((items) => {
      if (cancelled) return;
      setMessages(items);
    });
    return () => {
      cancelled = true;
    };
  }, [conversationId, userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, isSending]);

  const latestActionablePhqMessageId = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role !== 'assistant') continue;
      const phq = message.metadata?.phq9;
      const actionable =
        phq?.active &&
        !!phq.options?.length &&
        phq.phase !== 'completed' &&
        phq.phase !== 'deferred_crisis' &&
        phq.phase !== 'declined' &&
        phq.phase !== 'offer_pending';
      if (actionable) return answeredPhqMessageIds.has(message.id) ? null : message.id;
    }
    return null;
  }, [answeredPhqMessageIds, messages]);


  const lastAssistantMessageId = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === 'assistant' && message.content.trim()) return message.id;
    }
    return null;
  }, [messages]);

  const ensureConversation = async () => {
    if (conversationId) return conversationId;
    if (!userId) throw new Error('User belum masuk');
    const conversation = await chatAPI.createConversation(userId, 'Cerita baru');
    setConversationId(conversation.id);
    setConversations((items) => [conversation, ...items]);
    router.replace(`/chat?conversationId=${conversation.id}`);
    return conversation.id;
  };

  const submitMessage = async (content: string, sourcePhqMessageId?: string) => {
    const trimmed = content.trim();
    if (!trimmed || isSending || !userId) return;

    setSendError(null);
    setInput('');
    setIsSending(true);
    chatSounds.typing();
    const nextConversationId = await ensureConversation();
    const phqMessageToClose = sourcePhqMessageId || latestActionablePhqMessageId;
    if (phqMessageToClose) {
      setAnsweredPhqMessageIds((current) => new Set(current).add(phqMessageToClose));
    }
    const optimisticUser: Message = {
      id: `optimistic-${Date.now()}`,
      conversationId: nextConversationId,
      role: 'user',
      content: trimmed,
      status: 'sending',
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setMessages((items) => [...items, optimisticUser]);

    try {
      let response;
      if (chatResponseMode === 'stream') {
        const optimisticAssistant: Message = {
          id: `streaming-${Date.now()}`,
          conversationId: nextConversationId,
          role: 'assistant',
          content: '',
          status: 'sending',
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        setMessages((items) => [...items, optimisticAssistant]);
        setStreamingMessageId(optimisticAssistant.id);
        response = await chatAPI.streamMessage(
          {
            conversationId: nextConversationId,
            userId,
            content: trimmed,
            phq9_state: phq9StateByConversationRef.current[nextConversationId],
            cbt_state: cbtStateByConversationRef.current[nextConversationId],
          },
          (event) => {
            if (event.event === 'token') {
              chatSounds.stream();
              setMessages((items) =>
                items.map((message) =>
                  message.id === optimisticAssistant.id
                    ? { ...message, content: `${message.content}${event.data}`, updatedAt: Date.now() }
                    : message
                )
              );
            }
          }
        );
        setStreamingMessageId(null);
        setMessages((items) => items.filter((message) => message.id !== optimisticAssistant.id));
      } else {
        response = await chatAPI.sendMessage({
          conversationId: nextConversationId,
          userId,
          content: trimmed,
          phq9_state: phq9StateByConversationRef.current[nextConversationId],
          cbt_state: cbtStateByConversationRef.current[nextConversationId],
        });
      }
      if (response.phq9_state !== undefined) {
        phq9StateByConversationRef.current[nextConversationId] = response.phq9_state;
      }
      if (response.cbt_state !== undefined) {
        cbtStateByConversationRef.current[nextConversationId] = response.cbt_state;
      }
      setMessages((items) => [
        ...items.filter((message) => message.id !== optimisticUser.id),
        response.userMessage,
        response.assistantMessage,
      ]);
      chatSounds.complete();
      const nextItems = await chatAPI.getConversations(userId);
      setConversations(nextItems);
    } catch (error) {
      setStreamingMessageId(null);
      setMessages((items) =>
        items
          .filter((message) => !message.id.startsWith('streaming-'))
          .map((message) => (message.id === optimisticUser.id ? { ...message, status: 'failed' as const } : message))
      );
      setSendError(friendlyErrorMessage(error, 'Pesan gagal terkirim, coba lagi ya.'));
    } finally {
      setIsSending(false);
    }
  };

  const newChat = async () => {
    if (!userId) return;
    try {
      const conversation = await chatAPI.createConversation(userId, 'Cerita baru');
      setConversationId(conversation.id);
      setMessages([]);
      setAnsweredPhqMessageIds(new Set());
      setConversations((items) => [conversation, ...items]);
      router.replace(`/chat?conversationId=${conversation.id}`);
    } catch (error) {
      addToast(friendlyErrorMessage(error, 'Gagal membuat sesi baru, coba lagi ya.'), 'error');
    }
  };

  const chooseConversation = (id: string) => {
    setConversationId(id);
    setAnsweredPhqMessageIds(new Set());
    router.replace(`/chat?conversationId=${id}`);
  };

  const backToSessions = () => {
    setConversationId(null);
    setMessages([]);
    setAnsweredPhqMessageIds(new Set());
    router.replace('/chat');
  };

  const renameCurrentConversation = async () => {
    if (!conversationId) return;
    const current = conversations.find((conversation) => conversation.id === conversationId);
    const nextTitle = window.prompt('Judul sesi baru', current?.title || 'Cerita baru')?.trim();
    if (!nextTitle) return;
    try {
      const updated = await chatAPI.updateConversationTitle(conversationId, nextTitle);
      setConversations((items) => items.map((item) => (item.id === conversationId ? { ...item, ...updated } : item)));
    } catch (error) {
      addToast(friendlyErrorMessage(error, 'Gagal mengganti judul sesi, coba lagi ya.'), 'error');
    }
  };

  const deleteCurrentConversation = async () => {
    if (!conversationId) return;
    const confirmed = window.confirm('Hapus sesi ini? Riwayat chat di sesi ini tidak akan tampil lagi.');
    if (!confirmed) return;
    try {
      const ok = await chatAPI.deleteConversation(conversationId);
      if (!ok) return;
      setConversations((items) => items.filter((item) => item.id !== conversationId));
      backToSessions();
    } catch (error) {
      addToast(friendlyErrorMessage(error, 'Gagal menghapus sesi, coba lagi ya.'), 'error');
    }
  };

  const playMessage = async (message: Message) => {
    if (playingMessageId) return;
    setPlayingMessageId(message.id);
    const audioElement = primeAudioElement();
    try {
      const result = await voiceAPI.synthesize({
        text: stripCrisisResourceBlock(message.content),
        voice_id: user?.preferredVoiceId,
        tts_model: (user?.preferredTtsModel as any) || 'v2_5_turbo',
        language_pref: user?.preferredLanguage || 'id',
      });
      if (!result.audio_output_base64) throw new Error('no audio returned');
      const src = dataUrlFromBase64(result.audio_output_base64, result.audio_output_format);
      const handle = createAudioPlayer(src, undefined, audioElement);
      await handle.done;
    } catch (error) {
      console.warn('Chat: message playback failed', error);
    } finally {
      setPlayingMessageId(null);
    }
  };

  const regenerateMessage = async (message: Message) => {
    if (!conversationId || regeneratingMessageId) return;
    setRegeneratingMessageId(message.id);
    try {
      const response = await chatAPI.regenerateMessage(conversationId, message.id, {
        userId: userId || undefined,
        phq9_state: phq9StateByConversationRef.current[conversationId],
        cbt_state: cbtStateByConversationRef.current[conversationId],
      });
      if (response.phq9_state !== undefined) phq9StateByConversationRef.current[conversationId] = response.phq9_state;
      if (response.cbt_state !== undefined) cbtStateByConversationRef.current[conversationId] = response.cbt_state;
      setMessages((items) => items.map((item) => (item.id === message.id ? response.assistantMessage : item)));
    } catch (error) {
      setSendError(friendlyErrorMessage(error, 'Gagal membuat ulang balasan, coba lagi ya.'));
    } finally {
      setRegeneratingMessageId(null);
    }
  };

  if (!conversationId) {
    return (
      <V2Shell showTopbar={false}>
        <SessionListView
          conversations={filteredConversations}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onChoose={chooseConversation}
          onNewChat={() => void newChat()}
        />
      </V2Shell>
    );
  }

  return (
    <V2Shell showTopbar={false} showBottomNav={false}>
      <main
        className={`${chatRoomStyles.pageContainer} ${animationClasses.pageEnter}`}
        style={{ ...motionStyleVars({ durationMs: 300 }), height: `calc(100dvh - ${keyboardInset}px)` }}
      >
        <ChatHeader
          onBack={backToSessions}
          onVoice={() => router.push('/confession-space')}
          onRename={() => void renameCurrentConversation()}
          onDelete={() => void deleteCurrentConversation()}
        />

        <section data-chat-rail className={chatRoomStyles.chatRail}>
          <DateDivider label={formatChatDateDivider(messages[0]?.createdAt ?? Date.now())} delayMs={130} />

          {messages.length === 0 || messages[0]?.role === 'user' ? (
            <AssistantBubble
              showActions={false}
              message={{
                id: 'welcome',
                conversationId: conversationId || 'new',
                role: 'assistant',
                content: `Hai, ${name} \nGimana kabarmu hari ini?\nMau cerita apa nih?`,
                status: 'sent',
                createdAt: Date.now(),
                updatedAt: Date.now(),
              }}
            />
          ) : null}

          {messages.map((message, index) => {
            const previous = messages[index - 1];
            const showDivider = previous && isDifferentCalendarDay(previous.createdAt, message.createdAt);
            const isCrisisMessage = message.metadata?.crisisTier === '1' || message.metadata?.crisisTier === '2';
            const displayMessage = isCrisisMessage
              ? { ...message, content: stripCrisisResourceBlock(message.content) }
              : message;
            return (
              <Fragment key={message.id}>
                {showDivider ? <DateDivider label={formatChatDateDivider(message.createdAt)} /> : null}
                {message.role === 'assistant' ? (
                  <AssistantBubble
                    message={displayMessage}
                    showActions={Boolean(displayMessage.content.trim())}
                    isStreaming={message.id === streamingMessageId}
                    onPhqAnswer={(label) => {
                      void submitMessage(label, message.id);
                    }}
                    phqDisabled={isSending || latestActionablePhqMessageId !== message.id}
                    onPlay={() => void playMessage(message)}
                    isPlaying={playingMessageId === message.id}
                    showRegenerate={message.id === lastAssistantMessageId}
                    onRegenerate={() => void regenerateMessage(message)}
                    isRegenerating={regeneratingMessageId === message.id}
                  />
                ) : (
                  <UserBubble message={message} />
                )}
                {isCrisisMessage ? <HotlineWarningCard /> : null}
              </Fragment>
            );
          })}

          {isSending && chatResponseMode !== 'stream' ? (
            <div className={`flex items-center gap-2 pl-2 text-sm text-[var(--v2-muted)] ${animationClasses.chatBubbleIn}`}>
              <Loader2 className="h-4 w-4 animate-spin" /> AXIS sedang menulis...
            </div>
          ) : null}
          <div ref={bottomRef} />
        </section>

        {sendError ? (
          <p className="-mx-[22px] px-[22px] pb-1 text-[12px] font-semibold text-[var(--v2-clay-subtle)]">{sendError}</p>
        ) : null}
        {messageLimit.limit !== null && messageLimit.remaining !== null ? (
          <p className="-mx-[22px] px-[22px] pb-1 text-[11px] font-medium text-[var(--v2-muted)]">
            {messageLimit.remaining}/{messageLimit.limit} pesan hari ini
          </p>
        ) : null}
        <ChatComposer
          value={input}
          onChange={setInput}
          onSubmit={() => void submitMessage(input)}
          disabled={isSending}
        />
      </main>
    </V2Shell>
  );
}

export default function ChatPage() {
  return (
    <AuthRequired>
      <Suspense fallback={<main className="v2-screen v2-center">Memuat chat...</main>}>
        <ChatPageContent />
      </Suspense>
    </AuthRequired>
  );
}

function DateDivider({ label, delayMs = 0 }: { label: string; delayMs?: number }) {
  return (
    <p
      className={`mx-auto w-fit rounded-full bg-[var(--v2-bg-light-10)] px-3.5 py-1 text-[11px] font-semibold text-[var(--v2-c-8d8880)] ${animationClasses.staggerItem}`}
      style={motionStyleVars({ delayMs })}
    >
      {label}
    </p>
  );
}

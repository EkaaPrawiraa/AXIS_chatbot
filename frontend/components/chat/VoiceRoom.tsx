'use client';

import { motion } from 'framer-motion';
import { ArrowLeft, ChevronDown, MessageSquareText, Mic, Plus, Radio, Volume2, X } from 'lucide-react';
import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { useT } from '@/lib/i18n';
import { useVoiceVisualizer } from '@/hooks/useVoiceVisualizer';
import type { Conversation, ID, Message } from '@/models';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { VoiceInteractionStatus } from './VoiceInteractionPanel';

interface VoiceRoomProps {
  status: VoiceInteractionStatus;
  transcript?: string;
  error?: string | null;
  isRecording?: boolean;
  disabled?: boolean;
  conversationActive?: boolean;
  audioLevel?: number;
  hoverHint?: string;
  userTranscript?: string;
  assistantTranscript?: string;
  sessionMessages?: Message[];
  showMiniSession?: boolean;
  conversations?: Conversation[];
  selectedConversationId?: ID | null;
  onSelectConversation?: (id: ID | null) => void;
  onToggleMiniSession?: () => void;
  onToggleVoice?: () => void;
  onBack?: () => void;
}

export function VoiceRoom({
  status,
  transcript,
  error,
  isRecording,
  disabled,
  conversationActive,
  audioLevel: audioLevelOverride,
  hoverHint,
  userTranscript,
  assistantTranscript,
  sessionMessages,
  showMiniSession,
  conversations,
  selectedConversationId,
  onSelectConversation,
  onToggleMiniSession,
  onToggleVoice,
  onBack,
}: VoiceRoomProps) {
  const t = useT();
  const generatedAudioLevel = useVoiceVisualizer(status);
  const audioLevel = audioLevelOverride ?? generatedAudioLevel;

  const subtitle = useMemo(() => {
    if (error) return error;
    if (status === 'listening') {
      return t('voiceRoomListeningEllipsis');
    }
    if (status === 'processing') {
      return transcript || userTranscript || '';
    }
    if (status === 'speaking') {
      return assistantTranscript || '';
    }
    return '';
  }, [assistantTranscript, error, status, transcript, userTranscript]);
  const subtitleIsMarkdown = status === 'speaking' && !error;

  return (
    <motion.section
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className="relative flex h-full min-h-[calc(100dvh-4rem)] min-w-0 flex-col overflow-hidden bg-background text-foreground"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_36%,color-mix(in_oklab,var(--accent)_34%,transparent),transparent_34%),radial-gradient(circle_at_20%_78%,color-mix(in_oklab,var(--axis-wash)_62%,transparent),transparent_42%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,color-mix(in_oklab,var(--border)_20%,transparent)_1px,transparent_1px),linear-gradient(180deg,color-mix(in_oklab,var(--border)_20%,transparent)_1px,transparent_1px)] bg-[size:72px_72px] opacity-40" />

      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="absolute left-5 top-5 z-10 inline-flex items-center gap-2 rounded-xl border border-border bg-card/78 px-3 py-2 text-sm font-medium text-foreground shadow-[var(--axis-shadow-soft)] backdrop-blur transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-ring/45"
          aria-label={t('back')}
        >
          <ArrowLeft className="size-4" />
          {t('back')}
        </button>
      )}

      {onSelectConversation && !conversationActive && (
        <ConversationPicker
          conversations={conversations || []}
          selectedConversationId={selectedConversationId ?? null}
          onSelect={onSelectConversation}
        />
      )}
      {conversationActive && onToggleMiniSession && (
        <button
          type="button"
          onClick={onToggleMiniSession}
          className="absolute right-5 top-5 z-20 inline-flex items-center gap-2 rounded-xl border border-border bg-card/78 px-3 py-2 text-sm font-medium text-foreground shadow-[var(--axis-shadow-soft)] backdrop-blur transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-ring/45"
          aria-label={showMiniSession ? t('hideMiniSession') : t('showMiniSession')}
        >
          {showMiniSession ? <X className="size-4" /> : <MessageSquareText className="size-4" />}
          <span>{showMiniSession ? t('hideMiniSession') : t('showMiniSession')}</span>
        </button>
      )}
      {conversationActive && showMiniSession && (
        <MiniSessionPanel messages={sessionMessages || []} />
      )}

      <main className="relative flex min-h-0 flex-1 flex-col items-center justify-center px-5 py-20 text-center">
        <h1 className="font-mono text-[clamp(1.4rem,4vw,3.5rem)] font-semibold uppercase leading-none tracking-[0.22em] text-foreground">
          YOUR SAFE SPACE
        </h1>
        <div className="mt-5 min-h-7" />

        <VoiceRoomMic
          status={status}
          audioLevel={audioLevel}
          disabled={disabled}
          isRecording={isRecording}
          conversationActive={conversationActive}
          hoverHint={hoverHint}
          onToggleVoice={onToggleVoice}
        />

        <div className="mt-10 min-h-[4.5rem] w-full max-w-3xl px-3">
          {subtitle && (
            <motion.div
              key={status}
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{
                layout: { duration: 0.32, ease: [0.22, 1, 0.36, 1] },
                opacity: { duration: 0.28, ease: [0.22, 1, 0.36, 1] },
                y: { duration: 0.28, ease: [0.22, 1, 0.36, 1] },
              }}
              className={cn(
                'mx-auto text-base leading-7 transition-colors [overflow-wrap:anywhere] sm:text-lg',
                error ? 'text-destructive' : 'text-foreground'
              )}
            >
              {status === 'listening' && !error ? (
                <div className="inline-flex items-center gap-3 font-medium text-muted-foreground">
                  <span>{subtitle}</span>
                  <span className="axis-listening-wave" aria-hidden="true">
                    {[0, 1, 2].map((i) => (
                      <span key={i} style={{ animationDelay: `${i * 130}ms` }} />
                    ))}
                  </span>
                </div>
              ) : subtitleIsMarkdown ? (
                <div className="relative">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 text-left last:mb-0">{children}</ul>,
                      ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 text-left last:mb-0">{children}</ol>,
                      li: ({ children }) => <li className="pl-1">{children}</li>,
                      strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                      em: ({ children }) => <em className="text-foreground/90">{children}</em>,
                      a: ({ children, href }) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          className="font-medium underline decoration-border underline-offset-4 transition-colors hover:decoration-foreground"
                        >
                          {children}
                        </a>
                      ),
                      code: ({ children }) => (
                        <code className="rounded-md border border-border bg-muted/55 px-1.5 py-0.5 font-mono text-[0.9em]">
                          {children}
                        </code>
                      ),
                      pre: ({ children }) => (
                        <pre className="mb-2 overflow-x-auto rounded-xl border border-border bg-muted/45 p-3 text-left font-mono text-xs leading-6 last:mb-0">
                          {children}
                        </pre>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="mb-2 border-l-2 border-border pl-4 text-left text-muted-foreground last:mb-0">
                          {children}
                        </blockquote>
                      ),
                    }}
                  >
                    {subtitle}
                  </ReactMarkdown>
                  {status === 'speaking' && (
                    <span className="axis-voice-caret" aria-hidden="true" />
                  )}
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{subtitle}</p>
              )}
            </motion.div>
          )}
        </div>
      </main>
    </motion.section>
  );
}

function MiniSessionPanel({ messages }: { messages: Message[] }) {
  const t = useT();
  const visibleMessages = messages.slice(-12);

  return (
    <motion.aside
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 18 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className="absolute right-5 top-20 z-20 flex h-[min(26rem,calc(100dvh-8rem))] w-[min(22rem,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-border bg-card/88 shadow-[var(--axis-shadow)] backdrop-blur-xl"
    >
      <div className="border-b border-border px-4 py-3">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          {t('miniSession')}
        </p>
      </div>
      <div className="min-h-0 overflow-y-auto px-3 py-3">
        {visibleMessages.length === 0 ? (
          <p className="px-1 py-6 text-sm leading-6 text-muted-foreground">{t('miniSessionEmpty')}</p>
        ) : (
          <div className="space-y-3">
            {visibleMessages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'w-[92%] rounded-2xl px-3 py-2 text-sm leading-6 [overflow-wrap:anywhere]',
                  message.role === 'user'
                    ? 'ml-auto bg-primary text-primary-foreground'
                    : 'mr-auto bg-muted/55 text-foreground'
                )}
              >
                <p className="mb-1 font-mono text-[9px] font-semibold uppercase tracking-[0.14em] opacity-60">
                  {message.role === 'user' ? t('you') : 'AXIS'}
                </p>
                <div className="axis-markdown axis-markdown-compact break-words text-sm leading-6">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
                      ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
                      li: ({ children }) => <li className="pl-1">{children}</li>,
                      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                      em: ({ children }) => <em>{children}</em>,
                      code: ({ children }) => (
                        <code className="rounded border border-current/15 bg-current/10 px-1 py-0.5 font-mono text-[0.9em]">
                          {children}
                        </code>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.aside>
  );
}

function VoiceRoomMic({
  status,
  audioLevel,
  disabled,
  isRecording,
  conversationActive,
  hoverHint,
  onToggleVoice,
}: {
  status: VoiceInteractionStatus;
  audioLevel: number;
  disabled?: boolean;
  isRecording?: boolean;
  conversationActive?: boolean;
  hoverHint?: string;
  onToggleVoice?: () => void;
}) {
  const t = useT();
  const Icon = status === 'speaking' ? Volume2 : status === 'listening' ? Radio : Mic;
  const isProcessing = status === 'processing';
  const active = status !== 'idle' || Boolean(conversationActive);
  const scale = 1 + audioLevel * (active ? 0.22 : 0.04);

  return (
    <button
      type="button"
      onClick={() => {
        if (!disabled) onToggleVoice?.();
      }}
      disabled={disabled}
      className="group relative mt-14 flex size-52 items-center justify-center rounded-full outline-none transition-transform duration-300 hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-70 sm:size-64"
      aria-label={isRecording ? t('stopAndSendVoiceMessage') : t('recordVoiceMessage')}
    >
      {[1, 1.34, 1.72].map((ring, index) => (
        <motion.span
          key={ring}
          className="absolute rounded-full border border-primary/14"
          animate={{
            width: 148 * ring + audioLevel * (46 + index * 20),
            height: 148 * ring + audioLevel * (46 + index * 20),
            opacity: active ? 0.36 + audioLevel * 0.26 - index * 0.07 : 0.22 - index * 0.05,
          }}
          transition={{ type: 'spring', stiffness: 100, damping: 18 }}
        />
      ))}
      {active && (
        <motion.span
          className={cn(
            'absolute size-40 rounded-full border sm:size-48',
            isProcessing ? 'border-primary/28' : 'border-primary/22'
          )}
          animate={
            isProcessing
              ? { scale: [1, 1.18, 1], opacity: [0.42, 0.18, 0.42] }
              : { scale: [1, 1.82], opacity: [0.38, 0] }
          }
          transition={
            isProcessing
              ? { duration: 1.05, repeat: Infinity, ease: [0.45, 0, 0.2, 1] }
              : { duration: 1.5, repeat: Infinity, ease: [0.22, 1, 0.36, 1] }
          }
        />
      )}
      {isProcessing && (
        <motion.span
          className="absolute size-44 rounded-full border border-transparent bg-[conic-gradient(from_0deg,transparent_0deg,color-mix(in_oklab,var(--primary)_55%,transparent)_78deg,transparent_142deg,transparent_360deg)] p-px sm:size-52"
          animate={{ rotate: 360 }}
          transition={{ duration: 1.25, repeat: Infinity, ease: 'linear' }}
        >
          <span className="block size-full rounded-full bg-background/70" />
        </motion.span>
      )}
      <motion.span
        className={cn(
          'relative z-10 flex size-36 items-center justify-center rounded-full border border-primary bg-primary text-primary-foreground shadow-[0_26px_76px_rgba(53,48,42,0.22)] sm:size-44',
          conversationActive && 'ring-4 ring-primary/10',
          isProcessing && 'bg-primary/95'
        )}
        animate={{ scale }}
        transition={{ type: 'spring', stiffness: 130, damping: 16 }}
      >
        {isProcessing ? <ProcessingGlyph /> : <Icon className="size-11 sm:size-14" />}
      </motion.span>
      <span className="pointer-events-none absolute bottom-2 left-1/2 z-20 w-[min(18rem,80vw)] -translate-x-1/2 translate-y-2 rounded-2xl border border-border bg-card/92 px-4 py-3 text-center text-xs font-medium leading-5 text-foreground opacity-0 shadow-[var(--axis-shadow)] backdrop-blur transition-[opacity,transform] duration-200 group-hover:translate-y-0 group-hover:opacity-100 group-focus-visible:translate-y-0 group-focus-visible:opacity-100">
        {hoverHint || t('voiceRoomStartHint')}
      </span>
    </button>
  );
}

function ProcessingGlyph() {
  return (
    <span className="relative flex size-16 items-center justify-center sm:size-20" aria-hidden="true">
      <motion.span
        className="absolute size-full rounded-full border border-primary-foreground/25"
        animate={{ scale: [0.78, 1.05, 0.78], opacity: [0.48, 0.18, 0.48] }}
        transition={{ duration: 1.25, repeat: Infinity, ease: [0.45, 0, 0.2, 1] }}
      />
      <span className="flex items-center gap-1.5">
        {[0, 1, 2].map((index) => (
          <motion.span
            key={index}
            className="block size-2 rounded-full bg-primary-foreground sm:size-2.5"
            animate={{ y: [0, -7, 0], opacity: [0.45, 1, 0.45] }}
            transition={{
              duration: 0.72,
              repeat: Infinity,
              delay: index * 0.12,
              ease: [0.45, 0, 0.2, 1],
            }}
          />
        ))}
      </span>
    </span>
  );
}

function ConversationPicker({
  conversations,
  selectedConversationId,
  onSelect,
}: {
  conversations: Conversation[];
  selectedConversationId: ID | null;
  onSelect: (id: ID | null) => void;
}) {
  const t = useT();
  const selected = conversations.find((c) => c.id === selectedConversationId);
  const label = selected?.title?.trim() || t('newConversation');
  const recent = conversations.slice(0, 8);

  return (
    <div className="absolute right-5 top-5 z-10">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card/78 px-3 py-2 text-sm font-medium text-foreground shadow-[var(--axis-shadow-soft)] backdrop-blur transition-[border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-ring/45"
            aria-label={t('conversation')}
          >
            <span className="max-w-[10rem] truncate">{label}</span>
            <ChevronDown className="size-4 shrink-0 opacity-70" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-72">
          <DropdownMenuItem
            onSelect={() => onSelect(null)}
            className="gap-2"
          >
            <Plus className="size-4" />
            {t('newConversation')}
          </DropdownMenuItem>
          {recent.length > 0 && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuLabel className="text-[10px] font-mono font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                {t('recent')}
              </DropdownMenuLabel>
              {recent.map((c) => (
                <DropdownMenuItem
                  key={c.id}
                  onSelect={() => onSelect(c.id)}
                  className={cn(
                    'flex flex-col items-start gap-0.5',
                    c.id === selectedConversationId && 'bg-muted/55'
                  )}
                >
                  <span className="w-full truncate text-sm">
                    {c.title?.trim() || t('untitledConversation')}
                  </span>
                </DropdownMenuItem>
              ))}
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

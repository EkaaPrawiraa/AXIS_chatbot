'use client';

import { ChatResponseMode, Message } from '@/models';
import { Button } from '@/components/ui/button';
import { HotlineWarningCard } from './HotlineWarningCard';
import { Phq9Options } from './Phq9Options';
import { TypingIndicator } from './TypingIndicator';
import { Check, Copy, Loader2, Pause, Play, RotateCcw, Trash2, UserRound } from 'lucide-react';
import { AxisAvatarIcon } from '@/components/icons';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { useT } from '@/lib/i18n';

type AudioState = 'idle' | 'loading' | 'playing';

interface MessageBubbleProps {
  message: Message;
  onCopy?: (content: string) => void;
  onPlay?: (message: Message, onStarted: () => void) => Promise<void>;
  onStop?: () => void;
  onRegenerate?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  onSendMessage?: (text: string) => void;
  chatResponseMode?: ChatResponseMode;
}

export function MessageBubble({
  message,
  onCopy,
  onPlay,
  onStop,
  onRegenerate,
  onDelete,
  onSendMessage,
  chatResponseMode = 'normal',
}: MessageBubbleProps) {
  const t = useT();
  const isUser = message.role === 'user';
  const isStreaming = !isUser && message.status === 'sending';
  const [copied, setCopied] = useState(false);
  const [audioState, setAudioState] = useState<AudioState>('idle');
  const timestamp = formatMessageTimestamp(message.createdAt);

  const handleCopy = async () => {
    try {
      if (onCopy) {
        onCopy(message.content);
      } else {
        await copyTextToClipboard(message.content);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.warn('Failed to copy message to clipboard:', error);
    }
  };

  const handlePlayToggle = async () => {
    if (audioState !== 'idle') {
      onStop?.();
      setAudioState('idle');
      return;
    }
    if (!onPlay) return;
    setAudioState('loading');
    try {
      await onPlay(message, () => setAudioState('playing'));
    } finally {
      setAudioState('idle');
    }
  };

  return (
    <div
      className={cn(
        'mb-7 flex animate-in fade-in slide-in-from-bottom-2 duration-300',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'min-w-0 flex flex-col gap-2',
          isUser ? 'max-w-[min(38rem,82%)] items-end' : 'w-full max-w-3xl items-start'
        )}
      >
        <div className={cn('flex items-center gap-2 text-xs text-muted-foreground', isUser && 'flex-row-reverse')}>
          {isUser ? (
            <>
              <span className="flex size-6 items-center justify-center rounded-lg border border-primary/20 bg-primary text-primary-foreground">
                <UserRound className="size-3.5" />
              </span>
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em]">{t('you')}</span>
              {timestamp && <MessageTime value={timestamp} />}
            </>
          ) : (
            <>
              <span className="flex size-6 items-center justify-center rounded-lg border border-border bg-card text-foreground">
                <AxisAvatarIcon size={14} />
              </span>
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em]">AXIS</span>
              {timestamp && <MessageTime value={timestamp} />}
            </>
          )}
        </div>

        {isUser ? (
          <div className="w-fit max-w-full rounded-[1.25rem] rounded-tr-md border border-primary bg-primary px-4 py-3 text-primary-foreground shadow-[var(--axis-shadow-soft)] [overflow-wrap:anywhere]">
            <p className="whitespace-pre-wrap break-words text-sm leading-relaxed [overflow-wrap:anywhere]">{message.content}</p>
            {message.metadata?.transcript && message.metadata.transcript !== message.content && (
              <p className="mt-3 border-t border-primary-foreground/20 pt-3 text-xs leading-5 opacity-80 [overflow-wrap:anywhere]">
                {t('voiceTranscript')}: {message.metadata.transcript}
              </p>
            )}
          </div>
        ) : (
          <div className="w-full min-w-0 break-words px-1 text-foreground [overflow-wrap:anywhere]">
            {isStreaming && message.content.length === 0 ? (
              <TypingIndicator mode={chatResponseMode === 'stream' ? 'thinking' : 'typing'} />
            ) : isStreaming ? (
              <div className="axis-markdown text-[15px] leading-7 [overflow-wrap:anywhere]">
                <MarkdownContent content={message.content} />
                <span className="axis-streaming-cursor inline-block h-5 w-1 align-baseline" aria-hidden="true" />
              </div>
            ) : (
              <div className="axis-markdown text-[15px] leading-7 [overflow-wrap:anywhere]">
                <MarkdownContent content={message.content} />
              </div>
            )}
            {!isStreaming && message.metadata?.transcript && message.metadata.transcript !== message.content && (
              <p className="mt-4 rounded-2xl border border-border bg-muted/35 px-4 py-3 text-xs leading-5 text-muted-foreground [overflow-wrap:anywhere]">
                {t('voiceTranscript')}: {message.metadata.transcript}
              </p>
            )}
            {!isStreaming && message.metadata?.phq9?.active && (
              <Phq9Options
                phase={message.metadata.phq9.phase}
                options={message.metadata.phq9.options}
                progress={message.metadata.phq9.progress}
                itemId={message.metadata.phq9.item_id}
                onSend={onSendMessage}
              />
            )}
          </div>
        )}

        {!isUser &&
          message.metadata?.safetyFlag === 'crisis' &&
          (message.metadata?.crisisTier === '1' || message.metadata?.crisisTier === '2') && (
            <HotlineWarningCard />
          )}

        {(message.metadata?.voice || message.metadata?.audioOutputBase64 || message.metadata?.audioOutputUrl) && (
          <div
            className={cn(
              'max-w-full truncate rounded-full border border-border bg-card px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground',
              isUser && 'border-primary/20 bg-primary/5'
            )}
          >
            {message.metadata?.voice?.tts_provider
              ? t('audioVia', message.metadata.voice.tts_provider)
              : t('audioAvailable')}
          </div>
        )}

        {!isStreaming && <div
          className={cn(
            'flex gap-1 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100',
            isUser ? 'pr-1' : 'pl-1'
          )}
        >
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => void handleCopy()}
            title={copied ? t('copied') : t('copyMessage')}
            className="h-7 w-7 rounded-lg p-0 text-muted-foreground"
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          </Button>

          {onPlay && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => void handlePlayToggle()}
              title={
                audioState === 'idle'
                  ? t('playMessageAudio')
                  : t('stopMessageAudio')
              }
              className="h-7 w-7 rounded-lg p-0 text-muted-foreground"
              disabled={false}
            >
              {audioState === 'loading' && (
                <Loader2 className="w-3 h-3 animate-spin" />
              )}
              {audioState === 'playing' && <Pause className="w-3 h-3" />}
              {audioState === 'idle' && <Play className="w-3 h-3" />}
            </Button>
          )}

          {!isUser && onRegenerate && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onRegenerate(message.id)}
              title={t('regenerateResponse')}
              className="h-7 w-7 rounded-lg p-0 text-muted-foreground"
            >
              <RotateCcw className="w-3 h-3" />
            </Button>
          )}

          {onDelete && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onDelete(message.id)}
              title={t('deleteMessage')}
              className="h-7 w-7 rounded-lg p-0 text-destructive hover:text-destructive"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
        </div>}
      </div>
    </div>
  );
}

async function copyTextToClipboard(text: string) {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  if (typeof document === 'undefined') return;
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

function MessageTime({ value }: { value: string }) {
  return (
    <span className="font-mono text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70">
      {value}
    </span>
  );
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
        em: ({ children }) => <em className="text-foreground/90">{children}</em>,
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-foreground underline decoration-border underline-offset-4 transition-colors hover:decoration-foreground"
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
          <pre className="mb-3 overflow-x-auto rounded-xl border border-border bg-muted/45 p-4 font-mono text-xs leading-6 last:mb-0">
            {children}
          </pre>
        ),
        blockquote: ({ children }) => (
          <blockquote className="mb-3 border-l-2 border-border pl-4 text-muted-foreground last:mb-0">
            {children}
          </blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function formatMessageTimestamp(timestamp: number | undefined) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '';

  const now = new Date();
  const isSameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isSameDay) {
    return new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

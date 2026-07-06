'use client';

import { ChatResponseMode, Message } from '@/models';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { ReactNode, useRef, useEffect } from 'react';
import { useT } from '@/lib/i18n';
import { MessageSquare } from 'lucide-react';

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  chatResponseMode?: ChatResponseMode;
  emptyContent?: ReactNode;
  onCopyMessage?: (content: string) => void;
  onPlayMessage?: (message: Message, onStarted: () => void) => Promise<void>;
  onStopMessage?: () => void;
  onRegenerate?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
  onSendMessage?: (text: string) => void;
}

export function MessageList({
  messages,
  isLoading,
  isStreaming,
  chatResponseMode = 'normal',
  emptyContent,
  onCopyMessage,
  onPlayMessage,
  onStopMessage,
  onRegenerate,
  onDeleteMessage,
  onSendMessage,
}: MessageListProps) {
  const t = useT();
  const endRef = useRef<HTMLDivElement>(null);
  const visibleMessages = messages.filter((message) => {
    if (message.role !== 'assistant' || message.status === 'sending') {
      return true;
    }
    return message.content.trim().length > 0;
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  if (isLoading) {
    return (
      <div className="mx-auto flex h-full w-full max-w-4xl items-center justify-center">
        <div className="w-full space-y-4">
          {[0, 1, 2].map((item) => (
            <div key={item} className="flex gap-3">
              <div className="size-10 animate-pulse rounded-2xl bg-muted" />
              <div className="flex-1 space-y-2 rounded-[1.25rem] border border-border bg-card p-4 shadow-[var(--axis-shadow-soft)]">
                <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
                <div className="h-3 w-5/6 animate-pulse rounded bg-muted" />
              </div>
            </div>
          ))}
          <p className="text-center font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            {t('loadingConversation')}
          </p>
        </div>
      </div>
    );
  }

  if (visibleMessages.length === 0 && !isStreaming) {
    if (emptyContent) {
      return <>{emptyContent}</>;
    }

    return (
      <div className="flex h-full items-center justify-center">
        <div className="axis-panel max-w-md rounded-[1.35rem] p-8 text-center">
          <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl border border-border bg-muted/50 text-primary">
            <MessageSquare className="size-5" />
          </div>
          <h3 className="mb-2 text-lg font-semibold tracking-[-0.01em]">{t('startConversation')}</h3>
          <p className="text-sm leading-7 text-muted-foreground">
            {t('startConversationDescription')}
          </p>
        </div>
      </div>
    );
  }

  const lastMessage = visibleMessages[visibleMessages.length - 1];
  const hasAssistantDraft = lastMessage?.role === 'assistant' && lastMessage.status === 'sending';

  return (
    <div className="flex w-full flex-col gap-1 pb-4">
      {visibleMessages.map((message) => (
        <div key={message.id} className="group">
          <MessageBubble
            message={message}
            onCopy={onCopyMessage}
            onPlay={onPlayMessage}
            onStop={onStopMessage}
            onRegenerate={onRegenerate}
            onDelete={onDeleteMessage}
            onSendMessage={onSendMessage}
            chatResponseMode={chatResponseMode}
          />
        </div>
      ))}

      {isStreaming && !hasAssistantDraft && (
        <TypingIndicator
          mode={chatResponseMode === 'stream' ? 'thinking' : 'typing'}
          showAvatar
          className="mt-2"
        />
      )}

      <div ref={endRef} />
    </div>
  );
}

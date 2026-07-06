'use client';

import { Message } from '@/models';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { useRef, useEffect } from 'react';

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  onCopyMessage?: (content: string) => void;
  onRegenerate?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
}

export function MessageList({
  messages,
  isLoading,
  isStreaming,
  onCopyMessage,
  onRegenerate,
  onDeleteMessage,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="w-full max-w-md space-y-3">
          <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
          <p className="text-muted-foreground">Loading conversation...</p>
        </div>
      </div>
    );
  }

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="axis-panel max-w-md p-8 text-center">
          <h3 className="mb-2 text-lg font-semibold">Start a Conversation</h3>
          <p className="text-muted-foreground">
            Begin a new chat with your AI companion. Share your thoughts, feelings, or ask for support.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 pb-4">
      {messages.map((message) => (
        <div key={message.id} className="group">
          <MessageBubble
            message={message}
            onCopy={onCopyMessage}
            onRegenerate={onRegenerate}
            onDelete={onDeleteMessage}
          />
        </div>
      ))}

      {isStreaming && (
        <div className="flex gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-border bg-card text-sm font-semibold">
            AI
          </div>
          <div className="flex-1">
            <TypingIndicator />
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}

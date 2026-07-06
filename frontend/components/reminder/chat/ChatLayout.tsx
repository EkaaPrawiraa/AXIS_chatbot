'use client';

import { ReactNode } from 'react';
import { Message } from '@/models';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

interface ChatLayoutProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  onSendMessage: (message: string) => void;
  onVoiceStart?: () => void;
  onCopyMessage?: (content: string) => void;
  onRegenerate?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
  children?: ReactNode;
}

export function ChatLayout({
  messages,
  isLoading,
  isStreaming,
  onSendMessage,
  onVoiceStart,
  onCopyMessage,
  onRegenerate,
  onDeleteMessage,
  children,
}: ChatLayoutProps) {
  return (
    <div className="flex h-full flex-col bg-background/55">
      {children && <div className="border-b border-border p-4">{children}</div>}

      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <MessageList
          messages={messages}
          isLoading={isLoading}
          isStreaming={isStreaming}
          onCopyMessage={onCopyMessage}
          onRegenerate={onRegenerate}
          onDeleteMessage={onDeleteMessage}
        />
      </div>

      <div className="border-t border-border bg-background/92 p-4 md:p-8">
        <ChatInput
          onSend={onSendMessage}
          onVoiceStart={onVoiceStart}
          isLoading={isLoading}
          isStreaming={isStreaming}
          placeholder="Share your thoughts..."
        />
      </div>
    </div>
  );
}

'use client';

import { ReactNode, useLayoutEffect, useRef, useState } from 'react';
import { ChatResponseMode, Message } from '@/models';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores';
import type { VoiceInteractionStatus } from './VoiceInteractionPanel';

interface ChatLayoutProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  chatResponseMode?: ChatResponseMode;
  onSendMessage: (message: string) => void;
  emptyContent?: ReactNode;
  onVoiceSend?: (audio: Blob, mimeType: string) => void;
  onVoiceStateChange?: (state: 'idle' | 'listening' | 'processing') => void;
  onToggleVoice?: () => void;
  voiceEnabled?: boolean;
  voiceStatus?: VoiceInteractionStatus;
  voiceTranscript?: string;
  voiceError?: string | null;
  isVoiceRecording?: boolean;
  onCopyMessage?: (content: string) => void;
  onPlayMessage?: (message: Message, onStarted: () => void) => Promise<void>;
  onStopMessage?: () => void;
  onRegenerate?: (messageId: string) => void;
  onDeleteMessage?: (messageId: string) => void;
  showComposer?: boolean;
  children?: ReactNode;
}

export function ChatLayout({
  messages,
  isLoading,
  isStreaming,
  chatResponseMode = 'normal',
  onSendMessage,
  emptyContent,
  onVoiceSend,
  onVoiceStateChange,
  onToggleVoice,
  voiceEnabled,
  voiceStatus = 'idle',
  voiceTranscript,
  voiceError,
  isVoiceRecording,
  onCopyMessage,
  onPlayMessage,
  onStopMessage,
  onRegenerate,
  onDeleteMessage,
  showComposer = true,
  children,
}: ChatLayoutProps) {
  const t = useT();
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const composerRef = useRef<HTMLDivElement>(null);
  const [composerHeight, setComposerHeight] = useState(156);

  useLayoutEffect(() => {
    if (!showComposer) {
      setComposerHeight(0);
      return;
    }
    const composer = composerRef.current;
    if (!composer) return;

    const updateComposerHeight = () => {
      setComposerHeight(Math.ceil(composer.getBoundingClientRect().height));
    };

    updateComposerHeight();
    const observer = new ResizeObserver(updateComposerHeight);
    observer.observe(composer);
    return () => observer.disconnect();
  }, [showComposer]);

  return (
    <div className="relative flex h-full min-h-0 max-h-full flex-col overflow-hidden bg-background/40">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_72%_0%,color-mix(in_oklab,var(--accent)_30%,transparent),transparent_28%)]" />
      {children && (
        <div className="relative border-b border-border/80 bg-background/82 p-4 backdrop-blur-xl">
          {children}
        </div>
      )}

      <div
        className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-5 sm:px-5 md:px-8 lg:px-10"
        style={{ paddingBottom: showComposer ? `${composerHeight + 28}px` : '1.5rem' }}
      >
        <MessageList
          messages={messages}
          isLoading={isLoading}
          isStreaming={isStreaming}
          chatResponseMode={chatResponseMode}
          emptyContent={emptyContent}
          onCopyMessage={onCopyMessage}
          onPlayMessage={onPlayMessage}
          onStopMessage={onStopMessage}
          onRegenerate={onRegenerate}
          onDeleteMessage={onDeleteMessage}
          onSendMessage={onSendMessage}
        />
      </div>

      {showComposer && (
        <div
          ref={composerRef}
          className={cn(
            'fixed bottom-0 left-0 right-0 z-40 border-t border-border/80 bg-background/88 px-3 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur-xl transition-[left] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] sm:px-4 md:px-5',
            sidebarCollapsed ? 'md:left-20' : 'md:left-72'
          )}
        >
          <div className="mx-auto w-full max-w-4xl">
            <ChatInput
              onSend={onSendMessage}
              onVoiceSend={onVoiceSend}
              onVoiceStateChange={onVoiceStateChange}
              onToggleVoice={onToggleVoice}
              voiceEnabled={voiceEnabled}
              voiceStatus={voiceStatus}
              voiceTranscript={voiceTranscript}
              voiceError={voiceError}
              isRecording={isVoiceRecording}
              isLoading={isLoading}
              isStreaming={isStreaming}
              placeholder={t('shareThoughts')}
            />
          </div>
        </div>
      )}
    </div>
  );
}

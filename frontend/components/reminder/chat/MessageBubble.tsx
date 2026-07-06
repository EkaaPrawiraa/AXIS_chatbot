'use client';

import { Message, MessageRole } from '@/models';
import { Button } from '@/components/ui/button';
import { Copy, RotateCcw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  message: Message;
  onCopy?: (content: string) => void;
  onRegenerate?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
}

export function MessageBubble({
  message,
  onCopy,
  onRegenerate,
  onDelete,
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (onCopy) {
      onCopy(message.content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        'mb-4 flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300',
        isUser && 'flex-row-reverse'
      )}
    >
      <div
        className={cn(
          'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-border text-sm font-semibold',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-card text-foreground'
        )}
      >
        {isUser ? 'You' : 'AI'}
      </div>

      <div className={cn('flex flex-col gap-2', isUser && 'items-end')}>
        <div
          className={cn(
            'max-w-2xl rounded-lg border px-4 py-3 break-words',
            isUser
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-border bg-card text-foreground'
          )}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            title="Copy message"
            className="h-6 w-6 p-0"
          >
            <Copy className="w-3 h-3" />
          </Button>

          {!isUser && onRegenerate && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRegenerate(message.id)}
              title="Regenerate response"
              className="h-6 w-6 p-0"
            >
              <RotateCcw className="w-3 h-3" />
            </Button>
          )}

          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(message.id)}
              title="Delete message"
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

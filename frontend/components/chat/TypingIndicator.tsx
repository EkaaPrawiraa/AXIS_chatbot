'use client';

import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { AxisAvatarIcon } from '@/components/icons';

interface TypingIndicatorProps {
  mode?: 'thinking' | 'typing';
  showAvatar?: boolean;
  className?: string;
}

export function TypingIndicator({
  mode = 'typing',
  showAvatar = false,
  className,
}: TypingIndicatorProps) {
  const t = useT();
  const isThinking = mode === 'thinking';

  return (
    <div className={cn('flex items-center gap-3', className)} role="status" aria-live="polite">
      {showAvatar && (
        <div className="axis-thinking-avatar">
          <AxisAvatarIcon size={16} />
        </div>
      )}
      <div className="axis-typing-inline">
        <span className="axis-typing-orb" aria-hidden="true" />
        <div className="min-w-0">
          <div className="text-sm font-semibold tracking-[-0.01em] text-foreground/88">
            {isThinking ? t('axisThinking') : t('companionTyping')}
          </div>
        </div>
        <div className="axis-typing-dots" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span key={i} style={{ animationDelay: `${i * 170}ms` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

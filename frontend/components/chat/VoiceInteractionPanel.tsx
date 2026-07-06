'use client';

import { motion } from 'framer-motion';
import { ChevronDown, ChevronUp, Mic, Radio, Volume2, WandSparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useT } from '@/lib/i18n';
import { useVoiceVisualizer } from '@/hooks/useVoiceVisualizer';
import { useMemo, useState } from 'react';

type VoiceInteractionStatus = 'idle' | 'listening' | 'processing' | 'speaking';

interface VoiceInteractionPanelProps {
  status: VoiceInteractionStatus;
  transcript?: string;
  error?: string | null;
  isRecording?: boolean;
  disabled?: boolean;
  onToggleVoice?: () => void;
}

export function VoiceInteractionPanel({
  status,
  transcript,
  error,
  isRecording,
  disabled,
  onToggleVoice,
}: VoiceInteractionPanelProps) {
  const t = useT();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const audioLevel = useVoiceVisualizer(status);

  const statusCopy = useMemo(() => {
    if (status === 'listening') {
      return {
        label: t('voiceListening'),
        helper: t('voiceRecordingHelp'),
        action: t('stopAndSendVoiceMessage'),
        Icon: Radio,
      };
    }
    if (status === 'processing') {
      return {
        label: t('voiceProcessing'),
        helper: transcript || t('voiceProcessingMessage'),
        action: t('voiceProcessing'),
        Icon: WandSparkles,
      };
    }
    if (status === 'speaking') {
      return {
        label: t('voiceSpeaking'),
        helper: transcript || t('audioAvailable'),
        action: t('voiceSpeaking'),
        Icon: Volume2,
      };
    }
    return {
      label: t('voiceReady'),
      helper: error || transcript || t('voiceIdleHelp'),
      action: t('recordVoiceMessage'),
      Icon: Mic,
    };
  }, [error, status, t, transcript]);

  const StatusIcon = statusCopy.Icon;
  const active = status !== 'idle';

  if (isCollapsed) {
    return (
      <div className="mb-3 flex w-full items-center justify-between rounded-2xl border border-border bg-card/95 px-3 py-2.5 shadow-[var(--axis-shadow-soft)]">
        <div className="flex min-w-0 items-center gap-3">
          <VoiceMark status={status} audioLevel={audioLevel} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-[-0.01em]">{statusCopy.label}</p>
            <p className="truncate text-xs text-muted-foreground">{statusCopy.action}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsCollapsed(false)}
          className="rounded-xl border border-border bg-background p-2 text-muted-foreground transition-colors hover:text-foreground"
          aria-label={t('showVoiceInteraction')}
        >
          <ChevronUp className="size-4" />
        </button>
      </div>
    );
  }

  return (
    <section
      role={onToggleVoice ? 'button' : undefined}
      tabIndex={onToggleVoice && !disabled ? 0 : undefined}
      onClick={() => {
        if (!disabled) onToggleVoice?.();
      }}
      onKeyDown={(event) => {
        if (!disabled && onToggleVoice && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault();
          onToggleVoice();
        }
      }}
      className={cn(
        'relative mb-3 overflow-hidden rounded-[1.25rem] border border-border bg-card/96 p-3 shadow-[var(--axis-shadow-soft)] transition-[border-color,box-shadow,opacity,transform] duration-300 sm:p-4',
        onToggleVoice && !disabled && 'cursor-pointer hover:-translate-y-0.5 hover:border-ring/45 hover:shadow-[var(--axis-shadow)]',
        disabled && 'cursor-not-allowed opacity-75'
      )}
      aria-label={isRecording ? t('stopAndSendVoiceMessage') : t('recordVoiceMessage')}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_0%,color-mix(in_oklab,var(--accent)_34%,transparent),transparent_42%)]" />
      <div className="relative flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <VoiceMark status={status} audioLevel={audioLevel} large />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold tracking-[-0.01em]">{statusCopy.label}</p>
              <span className="rounded-full border border-border bg-background/65 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                {active ? t('voiceLiveFeedback') : t('voiceInteraction')}
              </span>
            </div>
            <p className={cn('mt-1 line-clamp-2 text-xs leading-5', error ? 'text-destructive' : 'text-muted-foreground')}>
              {statusCopy.helper}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:shrink-0">
          <MiniWaveform active={active} audioLevel={audioLevel} />
          <StatusIcon className="hidden size-4 text-muted-foreground sm:block" />
          <button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              setIsCollapsed(true);
            }}
            className="rounded-xl border border-border bg-background/75 p-2 text-muted-foreground transition-colors hover:text-foreground"
            aria-label={t('hideVoiceInteraction')}
          >
            <ChevronDown className="size-4" />
          </button>
        </div>
      </div>
    </section>
  );
}

function VoiceMark({
  status,
  audioLevel,
  large,
}: {
  status: VoiceInteractionStatus;
  audioLevel: number;
  large?: boolean;
}) {
  const Icon = status === 'speaking' ? Volume2 : status === 'processing' ? WandSparkles : status === 'listening' ? Radio : Mic;
  const active = status !== 'idle';
  const scale = 1 + audioLevel * (active ? 0.16 : 0.04);

  return (
    <div className={cn('relative flex shrink-0 items-center justify-center', large ? 'size-12' : 'size-10')}>
      {active && (
        <motion.span
          className="absolute inset-0 rounded-full border border-primary/25"
          animate={{ scale: [1, 1.45], opacity: [0.35, 0] }}
          transition={{ duration: 1.45, repeat: Infinity, ease: [0.22, 1, 0.36, 1] }}
        />
      )}
      <motion.div
        className={cn(
          'relative z-10 flex items-center justify-center rounded-2xl border border-border bg-muted/45 text-foreground',
          large ? 'size-11' : 'size-9',
          active && 'border-primary bg-primary text-primary-foreground'
        )}
        animate={{ scale }}
        transition={{ type: 'spring', stiffness: 140, damping: 16 }}
      >
        <Icon className={large ? 'size-5' : 'size-4'} />
      </motion.div>
    </div>
  );
}

function MiniWaveform({ active, audioLevel }: { active: boolean; audioLevel: number }) {
  return (
    <div className="flex h-8 w-28 items-end gap-1 rounded-xl border border-border bg-background/55 px-2 py-1.5">
      {Array.from({ length: 12 }).map((_, index) => (
        <motion.span
          key={index}
          className="w-full rounded-full bg-primary/45"
          animate={{
            height: active ? `${24 + ((index * 19) % 58) * (0.32 + audioLevel)}%` : `${18 + (index % 4) * 8}%`,
            opacity: active ? 0.5 + audioLevel * 0.42 : 0.22,
          }}
          transition={{ type: 'spring', stiffness: 160, damping: 20 }}
        />
      ))}
    </div>
  );
}

export type { VoiceInteractionStatus };

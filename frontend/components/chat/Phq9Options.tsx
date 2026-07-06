'use client';

import { cn } from '@/lib/utils';
import { useState } from 'react';

interface Phq9OptionsProps {
  phase?: string;
  options?: Array<{ score: number | null; label: string }>;
  progress?: { current: number; total: number };
  itemId?: number;
  onSend?: (text: string) => void;
}

const OFFER_CHIPS = [
  { label: 'Ya, mulai', value: 'ya' },
  { label: 'Lewati dulu', value: 'tidak' },
];

export function Phq9Options({ phase, options, progress, itemId, onSend }: Phq9OptionsProps) {
  const [selectedValue, setSelectedValue] = useState<string | null>(null);

  if (!phase || phase === 'completed' || phase === 'deferred_crisis' || phase === 'declined' || phase === 'offer_pending') {
    return null;
  }

  const showOfferChips = phase === 'offered';
  const showAnswerChips = (phase === 'in_progress' || phase === 'awaiting_clar') && options && options.length > 0;

  if (!showOfferChips && !showAnswerChips) return null;

  const handleSelect = (value: string) => {
    if (selectedValue) return;
    setSelectedValue(value);
    onSend?.(value);
  };

  return (
    <div className="mt-3 flex flex-col gap-3">
      {progress && (
        <div className="flex items-center gap-3">
          <div className="flex-1 overflow-hidden rounded-full bg-muted/60" aria-hidden="true">
            <div
              className="h-1 rounded-full bg-primary transition-[width] duration-500"
              style={{ width: `${(progress.current / progress.total) * 100}%` }}
            />
          </div>
          <span
            className="shrink-0 font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground"
            aria-label={`Pertanyaan ${progress.current} dari ${progress.total}`}
          >
            {progress.current}/{progress.total}
          </span>
        </div>
      )}

      <div
        className="flex max-w-full flex-wrap gap-2"
        role="group"
        aria-label={showOfferChips ? 'Pilihan untuk memulai' : `Pilihan jawaban pertanyaan ${itemId ?? ''}`}
      >
        {showOfferChips &&
          OFFER_CHIPS.map((chip) => (
            <QuickReplyChip
              key={chip.value}
              label={chip.label}
              disabled={Boolean(selectedValue)}
              onClick={() => handleSelect(chip.value)}
            />
          ))}

        {showAnswerChips &&
          options!.map((opt) => (
            <QuickReplyChip
              key={`${opt.score ?? 'none'}-${opt.label}`}
              label={opt.label}
              disabled={Boolean(selectedValue)}
              onClick={() => handleSelect(String(opt.score))}
            />
          ))}
      </div>

      {phase === 'awaiting_clar' && (
        <p className="text-xs leading-5 text-muted-foreground">
          Jawaban tadi kurang jelas, pilih salah satu di atas atau ketik sendiri.
        </p>
      )}
    </div>
  );
}

function QuickReplyChip({ label, disabled, onClick }: { label: string; disabled?: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'rounded-2xl border border-border bg-card px-3.5 py-1.5 text-sm font-medium text-foreground',
        'shadow-[var(--axis-shadow-soft)] transition-[border-color,background-color,transform] duration-150',
        'hover:-translate-y-0.5 hover:border-ring/50 hover:bg-muted/60 disabled:pointer-events-none disabled:opacity-55',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'active:translate-y-0'
      )}
    >
      {label}
    </button>
  );
}

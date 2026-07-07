'use client';

import { Copy, Loader2, Play, RefreshCw } from '@/lib/assets';
import { useState } from 'react';

// Salin / Putar / Buat ulang pill bar; showRegenerate lets the caller hide "Buat ulang" for non-latest messages
export function MessageActions({
  content,
  onPlay,
  onRegenerate,
  showRegenerate = true,
  isPlaying = false,
  isRegenerating = false,
}: {
  content: string;
  onPlay?: () => void;
  onRegenerate?: () => void;
  showRegenerate?: boolean;
  isPlaying?: boolean;
  isRegenerating?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  const action =
    'v2-anim-pressable inline-flex items-center gap-1 whitespace-nowrap text-[11px] font-semibold text-[var(--v2-ink)] disabled:opacity-50';

  return (
    <div className="inline-flex w-fit flex-nowrap items-center gap-3.5 rounded-full border border-[var(--v2-line)] bg-[var(--v2-c-faf5ec)] px-3 py-[5px]">
      <button onClick={copy} className={action}>
        <Copy className="h-[11px] w-[11px]" /> {copied ? 'Tersalin' : 'Salin'}
      </button>
      <button onClick={onPlay} disabled={isPlaying} className={action}>
        {isPlaying ? <Loader2 className="h-[11px] w-[11px] animate-spin" /> : <Play className="h-[11px] w-[11px]" />} Putar
      </button>
      {showRegenerate ? (
        <button onClick={onRegenerate} disabled={isRegenerating} className={action}>
          {isRegenerating ? (
            <Loader2 className="h-[11px] w-[11px] animate-spin" />
          ) : (
            <RefreshCw className="h-[11px] w-[11px]" />
          )}
          Buat ulang
        </button>
      ) : null}
    </div>
  );
}

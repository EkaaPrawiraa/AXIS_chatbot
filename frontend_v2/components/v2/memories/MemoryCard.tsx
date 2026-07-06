'use client';

import Image from 'next/image';
import { ILLUSTRATIONS, Lock, MoreHorizontal } from '@/lib/assets';
import type { MemoryNode } from '@/models';

// Only 3 hand-illustrated watercolor arts exist — rather than rotating them
// arbitrarily by list position (which changes every time a card re-sorts or
// the list is filtered, so the same memory looks different on every visit),
// each node TYPE gets a fixed art so the same kind of memory always looks
// the same. Grouped thematically: experience/behaviour = "the journey"
// (path), subject/thought/topic = "reflection" (mug + plant, conversational),
// emotion/trigger/memory = "inner growth" (vase + leaves, rooted/nurtured).
const TYPE_ART: Record<string, string> = {
  experience: ILLUSTRATIONS.memoryArtExperience,
  behaviour: ILLUSTRATIONS.memoryArtExperience,
  subject: ILLUSTRATIONS.memoryArtSubject,
  thought: ILLUSTRATIONS.memoryArtSubject,
  topic: ILLUSTRATIONS.memoryArtSubject,
  emotion: ILLUSTRATIONS.memoryArtEmotion,
  trigger: ILLUSTRATIONS.memoryArtEmotion,
  memory: ILLUSTRATIONS.memoryArtEmotion,
};
const FALLBACK_ART = ILLUSTRATIONS.memoryArtSubject;

const TYPE_LABELS: Record<string, string> = {
  subject: 'Subjek',
  experience: 'Pengalaman',
  emotion: 'Emosi',
  trigger: 'Pemicu',
  thought: 'Pikiran',
  behaviour: 'Perilaku',
  topic: 'Topik',
  memory: 'Memori',
};

const SENSITIVE_LEVELS = new Set(['sensitive', 'trauma']);

export function isSensitiveNode(node: MemoryNode): boolean {
  const level = node.properties?.sensitivity_level as string | undefined;
  return level ? SENSITIVE_LEVELS.has(level.toLowerCase()) : false;
}

/** "Kemarin, 20.30" / "2 hari yang lalu" style timestamp like the v3 mock. */
export function formatMemoryTime(iso?: string): string {
  if (!iso) return 'Beberapa waktu lalu';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Beberapa waktu lalu';
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDiff = Math.round((startOfDay(now) - startOfDay(date)) / 86_400_000);
  const clock = date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }).replace(':', '.');
  if (dayDiff <= 0) return `Hari ini, ${clock}`;
  if (dayDiff === 1) return `Kemarin, ${clock}`;
  if (dayDiff < 7) return `${dayDiff} hari yang lalu`;
  return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
}

/**
 * Memory list card per the v3 design: watercolor art left, bold title,
 * soft timestamp, 3-line preview, lock badge for sensitive entries,
 * kebab menu, and a type chip bottom-right.
 */
export function MemoryCard({
  node,
  hideSensitive,
  onOpen,
}: {
  node: MemoryNode;
  hideSensitive: boolean;
  onOpen: () => void;
}) {
  const sensitive = isSensitiveNode(node);
  const hidden = sensitive && hideSensitive;
  const title = hidden ? 'Memori privat' : node.title || node.label;
  const preview = hidden
    ? 'Konten disembunyikan. Tekan "Tampilkan sensitif" untuk membukanya.'
    : node.preview || 'Belum ada ringkasan.';

  return (
    <article className="flex gap-3 rounded-[18px] border border-[#efe9db] bg-[#fdfbf4] p-2.5 shadow-[0_10px_22px_-18px_rgba(70,64,53,0.4)]">
      <Image
        src={TYPE_ART[node.type] || FALLBACK_ART}
        alt=""
        width={208}
        height={194}
        className="h-[92px] w-[78px] shrink-0 rounded-[12px] object-cover"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-[14.5px] font-bold leading-tight text-[var(--v2-ink)]">{title}</h3>
            <p className="text-[11px] font-medium text-[var(--v2-muted)]">
              {formatMemoryTime(node.updatedAt)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2 pt-0.5 text-[var(--v2-ink)]">
            {sensitive ? <Lock className="h-[13px] w-[13px]" strokeWidth={2.2} /> : null}
            <button onClick={onOpen} aria-label="Menu memori" className="v2-anim-pressable">
              <MoreHorizontal className="h-[15px] w-[15px]" />
            </button>
          </div>
        </div>
        <p className="mt-1 line-clamp-3 text-[11.5px] font-medium leading-[1.4] text-[#5f5b52]">{preview}</p>
        <div className="mt-1.5 flex justify-end">
          <span className="rounded-full bg-[#e9ead9] px-2.5 py-[2px] text-[10.5px] font-semibold text-[#5c6549]">
            {TYPE_LABELS[node.type] || node.type}
          </span>
        </div>
      </div>
    </article>
  );
}

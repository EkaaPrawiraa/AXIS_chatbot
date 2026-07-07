'use client';

import Image from 'next/image';
import { ILLUSTRATIONS, Lock, MoreHorizontal } from '@/lib/assets';
import type { MemoryNode } from '@/models';
import { memoryStyles } from '@/lib/styles/memoryStyles';

// TYPE_LABELS removed artwork definitions as per guidelines.

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
    ? 'Konten disembunyikan. Tekan "Tampilkan" untuk membukanya.'
    : node.preview || 'Belum ada ringkasan.';

  return (
    <article className={memoryStyles.cardWrapper}>
      <div className={memoryStyles.cardContentWrapper}>
        <div className={memoryStyles.cardHeader}>
          <div className="min-w-0 flex flex-col gap-0.5">
            <h3 className={memoryStyles.cardTitle}>
              {hidden ? (
                <span className={memoryStyles.cardTitleLocked}>
                  <Lock className="h-[13px] w-[13px]" strokeWidth={2.2} /> {title}
                </span>
              ) : (
                title
              )}
            </h3>
            <p className={memoryStyles.cardTime}>
              {formatMemoryTime(node.updatedAt)}
            </p>
          </div>
          <div className={memoryStyles.cardControls}>
            {!hidden && sensitive ? <Lock className="h-[13px] w-[13px]" strokeWidth={2.2} /> : null}
            <button onClick={onOpen} aria-label="Menu memori" className={memoryStyles.cardMenuBtn}>
              <MoreHorizontal className="h-[16px] w-[16px]" />
            </button>
          </div>
        </div>
        <p className={memoryStyles.cardPreview}>{preview}</p>
        <div className={memoryStyles.cardBadgeWrapper}>
          <span className={memoryStyles.cardBadge}>
            {TYPE_LABELS[node.type] || node.type}
          </span>
        </div>
      </div>
    </article>
  );
}

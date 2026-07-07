'use client';

import { BookOpen, Network, X } from '@/lib/assets';
import type { ComponentType } from 'react';
import { animationClasses } from '@/lib/animations';
import type { MemoryNodeType } from '@/models';

export interface RelationEntry {
  type: MemoryNodeType;
  label: string;
  title: string;
  description: string;
}

/**
 * Node detail bottom sheet per 22_knowledge_graph_node_detail: tapping a
 * hub satellite shows its icon, count, description, up to three curated
 * "Relasi utama" entries (per node-type relationships), and two actions —
 * a relation-graph affordance and the real "Buka memori" navigation.
 */
export function NodeDetailSheet({
  Icon,
  color,
  bg,
  label,
  count,
  description,
  relations,
  onSelectRelation,
  onViewRelations,
  onOpenMemories,
  onClose,
}: {
  Icon: ComponentType<{ className?: string; style?: React.CSSProperties }>;
  color: string;
  bg: string;
  label: string;
  count: number;
  description: string;
  relations: RelationEntry[];
  onSelectRelation?: (type: MemoryNodeType) => void;
  onViewRelations?: () => void;
  onOpenMemories: () => void;
  onClose: () => void;
}) {
  return (
    <div className={`fixed inset-0 z-[85] bg-black/40 ${animationClasses.sheetBackdropIn}`} onClick={onClose}>
      <aside
        onClick={(event) => event.stopPropagation()}
        className={`absolute inset-x-0 bottom-0 mx-auto max-h-[80dvh] w-[min(100%,540px)] overflow-y-auto rounded-t-[28px] bg-[var(--v2-c-f9f4ea)] px-4 pb-5 pt-2.5 shadow-2xl ${animationClasses.sheetUp}`}
      >
        <span className="mx-auto block h-[5px] w-14 rounded-full bg-[var(--v2-line-border)]" aria-hidden />

        <div className="mt-3 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid h-[54px] w-[54px] shrink-0 place-items-center rounded-full" style={{ backgroundColor: bg }}>
              <Icon className="h-[26px] w-[26px]" style={{ color }} />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[22px] font-bold leading-tight text-[var(--v2-ink)]">{label}</h2>
                <span className="rounded-full bg-[var(--v2-bg-light-10)] px-2.5 py-0.5 text-[11.5px] font-bold text-[var(--v2-muted-tertiary)]">
                  {count} memori
                </span>
              </div>
            </div>
          </div>
          <button onClick={onClose} aria-label="Tutup" className="v2-anim-pressable shrink-0 text-[var(--v2-ink)]">
            <X className="h-[20px] w-[20px]" />
          </button>
        </div>

        <p className="mt-3 text-[14px] font-medium leading-[1.5] text-[var(--v2-text-subdued)]">{description}</p>

        {relations.length ? (
          <>
            <p className="mt-4 text-[13.5px] font-bold text-[var(--v2-ink)]">Relasi utama</p>
            <div className="mt-2 divide-y divide-[var(--v2-line-light)] rounded-[18px] border border-[var(--v2-line-light)] bg-[var(--v2-bg-light-1)]">
              {relations.map((relation) => (
                <button
                  key={relation.type}
                  onClick={() => onSelectRelation?.(relation.type)}
                  className="flex w-full items-center gap-3 px-3.5 py-3 text-left"
                >
                  <span className="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full bg-[var(--v2-bg-light-10)] text-[var(--v2-ink)]">
                    <BookOpen className="h-[17px] w-[17px]" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13.5px] font-bold text-[var(--v2-ink)]">{relation.title}</span>
                    <span className="block text-[11.5px] font-medium leading-snug text-[var(--v2-muted-secondary)]">
                      {relation.description}
                    </span>
                  </span>
                  <span className="text-[var(--v2-muted-secondary)]">›</span>
                </button>
              ))}
            </div>
          </>
        ) : null}

        <div className="mt-4 flex items-center gap-2.5">
          <button
            onClick={onViewRelations}
            className="v2-anim-pressable flex h-[48px] flex-1 items-center justify-center gap-2 rounded-full border border-[var(--v2-line-lighter)] bg-[var(--v2-bg-light-1)] text-[14px] font-bold text-[var(--v2-ink)]"
          >
            <Network className="h-[16px] w-[16px]" /> Lihat relasi
          </button>
          <button
            onClick={onOpenMemories}
            className="v2-anim-pressable flex h-[48px] flex-1 items-center justify-center gap-2 rounded-full bg-[var(--v2-clay)] text-[14px] font-bold text-white shadow-[0_12px_22px_-12px_rgba(var(--v2-rgb-c36c45),0.9)]"
          >
            <BookOpen className="h-[16px] w-[16px]" /> Buka memori
          </button>
        </div>
      </aside>
    </div>
  );
}

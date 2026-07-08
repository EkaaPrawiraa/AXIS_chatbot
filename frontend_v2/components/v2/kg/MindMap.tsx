'use client';

import Avatar from 'boring-avatars';
import { Leaf } from '@/lib/assets';
import type { ComponentType } from 'react';
import type { MemoryNode } from '@/models';
import { useSessionStore } from '@/stores';

const CANVAS_W = 1180;
const CANVAS_H = 560;
const CENTER = { x: CANVAS_W / 2, y: 258 };

interface GroupDef {
  key: string;
  label: string;
  categories: string[];
  pill: string;
  chipBg: string;
  chipBorder: string;
  line: string;
  side: 'left' | 'right';
  y: number;
}

/** Six life-area groups per the v3 expanded-map mock, fed by real topic categories. */
const GROUPS: GroupDef[] = [
  { key: 'diri', label: 'Kesehatan Diri', categories: ['health'], pill: 'var(--v2-c-dfe4cd)', chipBg: 'var(--v2-c-e9ecdb)', chipBorder: 'var(--v2-c-d8ddc2)', line: 'var(--v2-c-9aa77e)', side: 'left', y: 108 },
  { key: 'hubungan', label: 'Hubungan', categories: ['social', 'family'], pill: 'var(--v2-c-eec5b7)', chipBg: 'var(--v2-c-f6e3da)', chipBorder: 'var(--v2-c-e8cdc0)', line: 'var(--v2-c-cd8465)', side: 'left', y: 258 },
  { key: 'karier', label: 'Karier & Pendidikan', categories: ['academic', 'career'], pill: 'var(--v2-c-f2e6bf)', chipBg: 'var(--v2-c-f6ecd2)', chipBorder: 'var(--v2-c-e9d9ae)', line: 'var(--v2-c-d9b264)', side: 'left', y: 408 },
  { key: 'mental', label: 'Kesehatan Mental', categories: ['mental_health'], pill: 'var(--v2-c-f2eddf)', chipBg: 'var(--v2-c-e9ecdb)', chipBorder: 'var(--v2-c-d8ddc2)', line: 'var(--v2-c-9aa77e)', side: 'right', y: 108 },
  { key: 'tujuan', label: 'Tujuan & Impian', categories: ['identity'], pill: 'var(--v2-c-e9dcbf)', chipBg: 'var(--v2-c-f6ecd2)', chipBorder: 'var(--v2-c-e9d9ae)', line: 'var(--v2-c-d9b264)', side: 'right', y: 258 },
  { key: 'lingkungan', label: 'Lingkungan & Kehidupan', categories: ['financial', 'other'], pill: 'var(--v2-c-dde3cd)', chipBg: 'var(--v2-c-e9ecdb)', chipBorder: 'var(--v2-c-d8ddc2)', line: 'var(--v2-c-9aa77e)', side: 'right', y: 408 },
];

const PILL_W = 250;
const PILL_H = 64;
const PILL_GAP_FROM_CENTER = 168; // horizontal gap between center and pill's inner edge
const CHIP_W = 190;
const CHIP_H = 42;
const CHIP_COL_GAP = 74; // gap between pill outer edge and chip column
const CHIP_STEP = 56;

function prettify(name: string): string {
  const text = name.replace(/_/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function groupTopics(topics: MemoryNode[], categories: string[]): string[] {
  return topics
    .filter((node) => categories.includes(String(node.properties?.category || 'other')))
    .slice(0, 3)
    .map((node) => prettify(String(node.properties?.name || node.title || node.label)));
}


export function MindMap({
  topics,
  userName,
  focusText = 'Menjadi versi terbaik diriku',
  onSelectTopic,
}: {
  topics: MemoryNode[];
  userName: string;
  focusText?: string;
  onSelectTopic?: (label: string) => void;
}) {
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);
  const layout = GROUPS.map((group) => {
    const dir = group.side === 'left' ? -1 : 1;
    const pillInnerX = CENTER.x + dir * PILL_GAP_FROM_CENTER;
    const pillOuterX = pillInnerX + dir * PILL_W;
    const chipInnerX = pillOuterX + dir * CHIP_COL_GAP;
    const chips = groupTopics(topics, group.categories);
    return { group, dir, pillInnerX, pillOuterX, chipInnerX, chips };
  });

  return (
    <div className="relative shrink-0" style={{ width: CANVAS_W, height: CANVAS_H }}>
      <svg className="absolute inset-0" width={CANVAS_W} height={CANVAS_H} aria-hidden>
        <g fill="none" stroke="var(--v2-c-e5dbc6)" strokeDasharray="5 7" strokeWidth="1.5">
          <circle cx={CENTER.x} cy={CENTER.y} r="128" />
          <circle cx={CENTER.x} cy={CENTER.y} r="205" />
        </g>
        {layout.map(({ group, dir, pillInnerX, pillOuterX, chipInnerX, chips }) => (
          <g key={group.key} fill="none" strokeWidth="2.4">
            <path
              stroke={group.line}
              d={`M ${CENTER.x + dir * 78} ${CENTER.y} C ${CENTER.x + dir * 130} ${CENTER.y}, ${
                pillInnerX - dir * 46
              } ${group.y}, ${pillInnerX} ${group.y}`}
            />
            {chips.map((_, index) => {
              const chipY = group.y + (index - (chips.length - 1) / 2) * CHIP_STEP;
              return (
                <path
                  key={index}
                  stroke={group.chipBorder}
                  strokeWidth="2"
                  d={`M ${pillOuterX} ${group.y} C ${pillOuterX + dir * 34} ${group.y}, ${
                    chipInnerX - dir * 30
                  } ${chipY}, ${chipInnerX} ${chipY}`}
                />
              );
            })}
          </g>
        ))}
      </svg>

      {layout.map(({ group, dir, pillInnerX, chipInnerX, chips }) => {
        const pillLeft = dir === -1 ? pillInnerX - PILL_W : pillInnerX;
        return (
          <div key={group.key}>
            <div
              className="absolute flex items-center justify-center gap-3 rounded-full px-2.5 text-[var(--v2-ink)] shadow-[0_12px_24px_-14px_rgba(var(--v2-rgb-464035),0.55)]"
              style={{ left: pillLeft, top: group.y - PILL_H / 2, width: PILL_W, height: PILL_H, backgroundColor: group.pill }}
            >
              <span className="text-[16.5px] font-bold leading-tight text-center">{group.label}</span>
            </div>

            {chips.map((chip, index) => {
              const chipY = group.y + (index - (chips.length - 1) / 2) * CHIP_STEP;
              const chipLeft = dir === -1 ? chipInnerX - CHIP_W : chipInnerX;
              return (
                <button
                  key={chip}
                  type="button"
                  onClick={() => onSelectTopic?.(chip)}
                  className="v2-anim-pressable absolute truncate rounded-full border px-4 text-[13.5px] font-semibold text-[var(--v2-ink)]"
                  style={{
                    left: chipLeft,
                    top: chipY - CHIP_H / 2,
                    width: CHIP_W,
                    height: CHIP_H,
                    backgroundColor: group.chipBg,
                    borderColor: group.chipBorder,
                  }}
                >
                  {chip}
                </button>
              );
            })}
          </div>
        );
      })}

      <div
        className="absolute flex -translate-x-1/2 flex-col items-center"
        style={{ left: CENTER.x, top: CENTER.y - 118 }}
      >
        <span className="block h-[156px] w-[156px] overflow-hidden rounded-full bg-[var(--v2-c-f6efe2)] shadow-[0_18px_34px_-18px_rgba(var(--v2-rgb-464035),0.6)] ring-8 ring-[var(--v2-c-fbf6ec)]">
          <Avatar
            size={156}
            name={user?.id ?? profile?.userId ?? "AXIS User"}
            variant="beam"
            colors={["#F2EFE8", "#D8DDC2", "#84A971", "#E7DFCC", "#F2D8C8"]}
          />
        </span>
        <p className="mt-3 text-[28px] font-bold leading-none text-[var(--v2-ink)]">{userName}</p>
     
        <p className="mt-0.5 text-[14.5px] font-medium text-[var(--v2-text-subdued)]">{focusText}</p>
      </div>
    </div>
  );
}

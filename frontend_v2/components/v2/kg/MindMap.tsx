'use client';

import Image from 'next/image';
import { Briefcase, Flower2, Heart, Home, Leaf, Star } from '@/lib/assets';
import type { ComponentType } from 'react';
import type { MemoryNode } from '@/models';
import { avatarSrcForUser } from '@/lib/avatar';
import { useSessionStore } from '@/stores';

const CANVAS_W = 1180;
const CANVAS_H = 560;
const CENTER = { x: CANVAS_W / 2, y: 258 };

interface GroupDef {
  key: string;
  label: string;
  categories: string[];
  Icon: ComponentType<{ className?: string; style?: React.CSSProperties }>;
  pill: string;
  iconColor: string;
  chipBg: string;
  chipBorder: string;
  line: string;
  side: 'left' | 'right';
  y: number;
}

/** Six life-area groups per the v3 expanded-map mock, fed by real topic categories. */
const GROUPS: GroupDef[] = [
  { key: 'diri', label: 'Kesehatan Diri', categories: ['health'], Icon: Leaf, pill: '#838c70', iconColor: '#5c7345', chipBg: '#e9ecdb', chipBorder: '#d8ddc2', line: '#9aa77e', side: 'left', y: 108 },
  { key: 'hubungan', label: 'Hubungan', categories: ['social', 'family'], Icon: Heart, pill: '#c26b4b', iconColor: '#c04f2f', chipBg: '#f6e3da', chipBorder: '#e8cdc0', line: '#cd8465', side: 'left', y: 258 },
  { key: 'karier', label: 'Karier & Pendidikan', categories: ['academic', 'career'], Icon: Briefcase, pill: '#d9a13d', iconColor: '#b98213', chipBg: '#f6ecd2', chipBorder: '#e9d9ae', line: '#d9b264', side: 'left', y: 408 },
  { key: 'mental', label: 'Kesehatan Mental', categories: ['mental_health'], Icon: Flower2, pill: '#a0a287', iconColor: '#5c7345', chipBg: '#e9ecdb', chipBorder: '#d8ddc2', line: '#9aa77e', side: 'right', y: 108 },
  { key: 'tujuan', label: 'Tujuan & Impian', categories: ['identity'], Icon: Star, pill: '#d9a13d', iconColor: '#b98213', chipBg: '#f6ecd2', chipBorder: '#e9d9ae', line: '#d9b264', side: 'right', y: 258 },
  { key: 'lingkungan', label: 'Lingkungan & Kehidupan', categories: ['financial', 'other'], Icon: Home, pill: '#b3b89d', iconColor: '#5c7345', chipBg: '#e9ecdb', chipBorder: '#d8ddc2', line: '#9aa77e', side: 'right', y: 408 },
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

/**
 * Landscape "Peta Memori" mind map per 09_knowledge_graph_expanded_rotate_phone:
 * dashed rings + avatar center, six tinted category pills with curved
 * connectors, and up to three real topic chips per category.
 */
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
  const avatarSrc = avatarSrcForUser(user?.id ?? profile?.userId);
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
        <g fill="none" stroke="#e5dbc6" strokeDasharray="5 7" strokeWidth="1.5">
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
              className="absolute flex items-center gap-3 rounded-full px-2.5 text-white shadow-[0_12px_24px_-14px_rgba(70,64,53,0.55)]"
              style={{ left: pillLeft, top: group.y - PILL_H / 2, width: PILL_W, height: PILL_H, backgroundColor: group.pill }}
            >
              <span className="grid h-[44px] w-[44px] shrink-0 place-items-center rounded-full bg-white">
                <group.Icon className="h-[22px] w-[22px]" style={{ color: group.iconColor }} />
              </span>
              <span className="text-[16.5px] font-bold leading-tight">{group.label}</span>
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
        <span className="block h-[156px] w-[156px] overflow-hidden rounded-full bg-[#f6efe2] shadow-[0_18px_34px_-18px_rgba(70,64,53,0.6)] ring-8 ring-[#fbf6ec]">
          <Image
            src={avatarSrc}
            alt={userName}
            width={186}
            height={186}
            unoptimized
            className="h-full w-full object-cover"
          />
        </span>
        <p className="mt-3 text-[28px] font-bold leading-none text-[var(--v2-ink)]">{userName}</p>
        <p className="mt-2 flex items-center gap-1.5 text-[14.5px] font-bold text-[var(--v2-ink)]">
          <Leaf className="h-[14px] w-[14px] text-[#a8854a]" fill="currentColor" /> Fokus hari ini
        </p>
        <p className="mt-0.5 text-[14.5px] font-medium text-[#5f5b52]">{focusText}</p>
      </div>
    </div>
  );
}

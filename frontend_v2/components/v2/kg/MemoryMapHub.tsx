'use client';

import Image from 'next/image';
import type { ComponentType } from 'react';
import type { MemoryNodeType } from '@/models';
import { avatarSrcForUser } from '@/lib/avatar';
import { MEMORY_TYPE_ICONS } from '@/lib/assets';
import { useSessionStore } from '@/stores';

export interface HubSpoke {
  type: MemoryNodeType;
  label: string;
  count: number;
}

// satellite order + styling, top then clockwise
export const SPOKE_STYLES: Record<
  string,
  { Icon: ComponentType<{ className?: string; style?: React.CSSProperties }>; bg: string; icon: string }
> = {
  experience: { Icon: MEMORY_TYPE_ICONS.experience, bg: 'var(--v2-c-dfe4cd)', icon: 'var(--v2-green-light)' },
  thought: { Icon: MEMORY_TYPE_ICONS.thought, bg: 'var(--v2-c-f2eddf)', icon: 'var(--v2-c-6a7258)' },
  memory: { Icon: MEMORY_TYPE_ICONS.memory, bg: 'var(--v2-c-e9dcbf)', icon: 'var(--v2-c-a8854a)' },
  emotion: { Icon: MEMORY_TYPE_ICONS.emotion, bg: 'var(--v2-c-eec5b7)', icon: 'var(--v2-c-c04f2f)' },
  topic: { Icon: MEMORY_TYPE_ICONS.topic, bg: 'var(--v2-c-dde3cd)', icon: 'var(--v2-green-secondary)' },
  behaviour: { Icon: MEMORY_TYPE_ICONS.behaviour, bg: 'var(--v2-c-f2e6bf)', icon: 'var(--v2-c-b98f2e)' },
  trigger: { Icon: MEMORY_TYPE_ICONS.trigger, bg: 'var(--v2-c-dfe4cd)', icon: 'var(--v2-green-light)' },
};

// connector relation labels per node type
export const SPOKE_RELATION_LABEL: Record<string, string> = {
  experience: 'membentuk',
  thought: 'mempengaruhi',
  memory: 'disimpan di',
  emotion: 'memicu',
  topic: 'terkait dengan',
  behaviour: 'mendorong',
  trigger: 'dipicu oleh',
};

// radial "Peta Memori" hub: user avatar in the middle, node-type satellites on a ring with connector lines
export function MemoryMapHub({
  spokes,
  userName,
  onSelect,
  size = 336,
}: {
  spokes: HubSpoke[];
  userName: string;
  onSelect?: (type: MemoryNodeType) => void;
  size?: number;
}) {
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);
  const avatarSrc = avatarSrcForUser(user?.id ?? profile?.userId);
  const center = size / 2;
  const ringRadius = size * 0.375;
  const satellite = size * 0.24;
  const positions = spokes.map((_, index) => {
    const angle = (index / spokes.length) * Math.PI * 2 - Math.PI / 2;
    return {
      x: center + Math.cos(angle) * ringRadius,
      y: center + Math.sin(angle) * ringRadius,
      angle,
    };
  });

  return (
    <div className="relative mx-auto" style={{ width: size, height: size }}>
      <svg className="absolute inset-0" width={size} height={size} aria-hidden>
        {positions.map((pos, index) => {
          const next = positions[(index + 1) % positions.length];
          const midX = (pos.x + next.x) / 2;
          const midY = (pos.y + next.y) / 2;
          return (
            <g key={index} stroke="var(--v2-c-d5c8ae)" strokeWidth="1.6" fill="var(--v2-c-cbbc9e)">
              <line x1={center} y1={center} x2={pos.x} y2={pos.y} />
              <line x1={pos.x} y1={pos.y} x2={next.x} y2={next.y} />
              <circle cx={midX} cy={midY} r="3.2" stroke="none" />
              <circle
                cx={(center + pos.x) / 2}
                cy={(center + pos.y) / 2}
                r="2.6"
                stroke="none"
              />
            </g>
          );
        })}
      </svg>

      {spokes.map((spoke, index) => {
        const style = SPOKE_STYLES[spoke.type] || SPOKE_STYLES.experience;
        const pos = positions[index];
        return (
          <button
            key={spoke.type}
            type="button"
            onClick={() => onSelect?.(spoke.type)}
            className="v2-anim-pressable absolute z-10 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full text-center shadow-[0_10px_20px_-14px_rgba(var(--v2-rgb-464035),0.5)]"
            style={{ left: pos.x, top: pos.y, width: satellite, height: satellite, backgroundColor: style.bg }}
          >
            <style.Icon
              className="h-[22px] w-[22px]"
              style={{ color: style.icon }}
              {...(spoke.type === 'emotion' ? { fill: 'currentColor' } : {})}
            />
            <span className="mt-0.5 text-[12px] font-bold leading-tight text-[var(--v2-ink)]">{spoke.label}</span>
            <span className="text-[10px] font-medium text-[var(--v2-c-7d7869)]">{spoke.count} memori</span>
          </button>
        );
      })}

      <div
        className="absolute z-20 -translate-x-1/2 -translate-y-1/2"
        style={{ left: center, top: center }}
      >
        <div className="relative">
          <span
            className="block overflow-hidden rounded-full bg-[var(--v2-c-f6efe2)] shadow-[0_14px_26px_-16px_rgba(var(--v2-rgb-464035),0.6)] ring-4 ring-white/90"
            style={{ width: size * 0.24, height: size * 0.24 }}
          >
            <Image
              src={avatarSrc}
              alt={userName}
              width={93}
              height={93}
              unoptimized
              className="h-full w-full object-cover"
            />
          </span>
          <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 rounded-[10px] bg-white px-3 py-0.5 text-[13px] font-bold text-[var(--v2-ink)] shadow">
            Kamu
          </span>
        </div>
      </div>
    </div>
  );
}

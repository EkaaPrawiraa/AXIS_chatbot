'use client';

import type { ComponentType, ReactNode } from 'react';

/**
 * Profile settings row per the v3 design: tinted icon circle on the left,
 * small label + bold value + muted helper, optional accessory on the right.
 */
export function ProfileRow({
  Icon,
  label,
  value,
  helper,
  accessory,
  onClick,
}: {
  Icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  helper?: string;
  accessory?: ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(event) => {
        if (onClick && (event.key === 'Enter' || event.key === ' ')) onClick();
      }}
      className={`flex w-full items-center gap-3 rounded-[20px] bg-[#f6efe3] px-3.5 py-2.5 text-left ${
        onClick ? 'v2-anim-pressable cursor-pointer' : ''
      }`}
    >
      <span className="grid h-[44px] w-[44px] shrink-0 place-items-center rounded-full bg-[#efe6d4] text-[#5c6549]">
        <Icon className="h-[21px] w-[21px]" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[12.5px] font-bold text-[#6b7355]">{label}</span>
        <span className="block truncate text-[15.5px] font-bold leading-snug text-[var(--v2-ink)]">{value}</span>
        {helper ? (
          <span className="block text-[11.5px] font-medium leading-snug text-[#8a8477]">{helper}</span>
        ) : null}
      </span>
      {accessory ? <span className="shrink-0">{accessory}</span> : null}
    </div>
  );
}

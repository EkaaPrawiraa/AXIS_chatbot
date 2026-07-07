import Image from 'next/image';
import { ILLUSTRATIONS } from '@/lib/assets';
import { cn } from '@/lib/utils';

// AXIS brand mark: orange bud above two olive leaves, inline SVG so it stays crisp at any size
export function AxisMark({ className, size = 44 }: { className?: string; size?: number }) {
  return (
    <svg
      viewBox="0 0 44 40"
      width={size}
      height={(size * 40) / 44}
      className={cn('shrink-0', className)}
      aria-label="AXIS"
      role="img"
    >
      <circle cx="22" cy="7.5" r="6" fill="var(--v2-clay)" />
      <path
        d="M21 36 C12 36 4.5 30 3 20.5 C10.5 19.5 19 24 21 33 Z"
        fill="var(--v2-olive)"
      />
      <path
        d="M23 36 C32 36 39.5 30 41 20.5 C33.5 19.5 25 24 23 33 Z"
        fill="var(--v2-olive)"
      />
    </svg>
  );
}

/** The real AXIS app icon (docs/axis_mobile_v3/Ikon_AXIS_Aplikasi.png). */
export function AxisMonogram({ className, size = 44 }: { className?: string; size?: number }) {
  return (
    <span
      className={cn('block shrink-0 overflow-hidden rounded-[13px] shadow-[0_10px_24px_rgba(var(--v2-rgb-53432e),0.10)]', className)}
      style={{ width: size, height: size }}
    >
      <Image src={ILLUSTRATIONS.appIcon} alt="AXIS" width={size} height={size} className="h-full w-full object-cover" priority />
    </span>
  );
}

export function AxisWordmark({
  className,
  markSize = 44,
  mark = 'plant',
}: {
  className?: string;
  markSize?: number;
  mark?: 'plant' | 'monogram';
}) {
  return (
    <div className={cn('axis-wordmark', className)}>
      {mark === 'monogram' ? <AxisMonogram size={markSize} /> : <AxisMark size={markSize} />}
      <span>AXIS</span>
    </div>
  );
}

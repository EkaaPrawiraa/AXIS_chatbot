import Link from 'next/link';
import type { CSSProperties, ReactNode } from 'react';
import { cn } from '@/lib/utils';

// quick action tile: cream card, icon above short label
export function QuickActionCard({
  href,
  label,
  icon,
  className,
  style,
}: {
  href: string;
  label: string;
  icon: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <Link
      href={href}
      className={cn(
        'v2-anim-pressable flex h-[74px] flex-col items-center justify-center gap-1 rounded-[12px] border border-[var(--v2-line)] bg-[var(--v2-cream)] px-1 py-1.5 text-center',
        className
      )}
      style={style}
    >
      {icon}
      <span className="text-[11px] font-semibold leading-[1.15] text-[var(--v2-ink)]">{label}</span>
    </Link>
  );
}

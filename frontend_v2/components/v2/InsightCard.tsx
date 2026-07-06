import Image from 'next/image';
import Link from 'next/link';
import type { CSSProperties } from 'react';
import { ILLUSTRATIONS } from '@/lib/assets';
import { cn } from '@/lib/utils';

// "last session" insight card: illustration left, title, short recap, continue link
export function InsightCard({
  title,
  body,
  linkLabel,
  href,
  className,
  style,
}: {
  title: string;
  body: string;
  linkLabel: string;
  href: string;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <section className={cn('flex items-center gap-3 rounded-[14px] bg-[#f9f2e8] py-1.5 pl-2 pr-4', className)} style={style}>
      <Image
        src={ILLUSTRATIONS.homeInsight}
        alt=""
        width={195}
        height={200}
        className="v2-anim-image-float w-[74px] shrink-0 select-none"
      />
      <div className="min-w-0">
        <h3 className="line-clamp-2 text-[13px] font-bold leading-snug text-[var(--v2-ink)]">
          <span aria-hidden>✨ </span>
          {title}
        </h3>
        <p className="mt-0.5 line-clamp-2 text-[12px] font-medium leading-[1.35] text-[var(--v2-ink)]">{body}</p>
        <Link
          href={href}
          className="v2-anim-pressable inline-flex items-center gap-1.5 pt-0.5 text-[12px] font-bold text-[var(--v2-olive-link)]"
        >
          {linkLabel} <span aria-hidden>›</span>
        </Link>
      </div>
    </section>
  );
}

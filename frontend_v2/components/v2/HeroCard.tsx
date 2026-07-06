import Image from 'next/image';
import Link from 'next/link';
import type { CSSProperties } from 'react';
import { ILLUSTRATIONS } from '@/lib/assets';
import { cn } from '@/lib/utils';

/**
 * Home hero card: full-bleed watercolor background (cropped from the v3
 * reference) with an olive scrim over the text zone, heading, blurb, and a
 * clay CTA pill.
 */
export function HeroCard({
  title,
  body,
  ctaLabel,
  href,
  className,
  style,
}: {
  title: string;
  body: string;
  ctaLabel: string;
  href: string;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <section className={cn('relative h-[141px] overflow-hidden rounded-[14px]', className)} style={style}>
      <Image
        src={ILLUSTRATIONS.homeHero}
        alt=""
        width={811}
        height={340}
        className="v2-anim-image-float absolute inset-0 h-full w-full select-none object-cover"
      />
      <span
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'linear-gradient(90deg, #694f1b 0%, #ac8742e8 42%, #79826a00 62%)',
        }}
      />
      <div className="relative z-10 max-w-[180px] px-[15px] py-[11px]">
        <h2 className="text-[21px] font-bold leading-tight text-white">{title}</h2>
        <p className="mt-1 text-[12px] font-medium leading-[1.4] text-white/95">{body}</p>
        <Link
          href={href}
          className="v2-anim-pressable mt-2 inline-flex h-[30px] items-center gap-2.5 rounded-full bg-[var(--v2-clay)] px-[17px] text-[12.5px] font-bold"
          style={{ color: '#ffffff' }}
        >
          {ctaLabel} <span aria-hidden>→</span>
        </Link>
      </div>
    </section>
  );
}

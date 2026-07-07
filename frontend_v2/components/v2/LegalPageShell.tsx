'use client';

import Link from 'next/link';
import { ChevronLeft } from '@/lib/assets';

export function LegalPageShell({
  title,
  lastUpdated,
  children,
}: {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto min-h-screen max-w-[680px] px-5 pb-16 pt-6 text-[var(--v2-ink)]">
      <Link
        href="/"
        className="v2-anim-pressable inline-flex items-center gap-1 text-[13px] font-semibold text-[var(--v2-olive-deep)]"
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={2.4} />
        Kembali ke Beranda
      </Link>

      <h1 className="mt-5 text-[26px] font-bold leading-tight tracking-[-0.03em]">{title}</h1>
      <p className="mt-1.5 text-[12.5px] font-medium text-[var(--v2-muted)]">
        Terakhir diperbarui: {lastUpdated}
      </p>

      <div className="mt-6 space-y-6 text-[14px] leading-relaxed text-[var(--v2-gray-dark-4)] [&_h2]:text-[16px] [&_h2]:font-bold [&_h2]:tracking-[-0.01em] [&_h2]:text-[var(--v2-ink)] [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_li]:leading-relaxed [&_a]:font-semibold [&_a]:text-[var(--v2-olive-link)] [&_a]:underline">
        {children}
      </div>
    </main>
  );
}

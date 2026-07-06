'use client';

import Image from 'next/image';
import { Frown, ILLUSTRATIONS, Laugh, Meh, Smile } from '@/lib/assets';
import type { CSSProperties } from 'react';
import { cn } from '@/lib/utils';
import { useMoodTrend, useSubmitMood } from '@/hooks';
import { useSessionStore } from '@/stores';

const MOODS = [
  { value: 1, label: 'Sangat sedih', Icon: Frown, color: '#bf4f33' },
  { value: 2, label: 'Sedih', Icon: Frown, color: '#cd7434' },
  { value: 3, label: 'Biasa saja', Icon: Meh, color: '#d5a02e' },
  { value: 4, label: 'Cukup baik', Icon: Smile, color: '#7d8f61' },
  { value: 5, label: 'Senang', Icon: Laugh, color: '#6f8f5b' },
];

function todayJakartaDate(): string {
  // matches backend's Asia/Jakarta calendar-day convention for mood_date
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jakarta' });
}

// daily mood check card; selecting a mood upserts today's score for real, the context builder reads it into the system prompt
export function MoodCheckCard({
  className,
  style,
}: {
  className?: string;
  style?: CSSProperties;
}) {
  const userId = useSessionStore((state) => state.userId);
  const { data: trend } = useMoodTrend(userId, 1);
  const submitMood = useSubmitMood();

  const todayEntry = trend?.find((entry) => entry.date === todayJakartaDate());
  const selectedValue = submitMood.isPending ? submitMood.variables : todayEntry?.score;

  return (
    <section className={cn('relative flex items-center gap-3 rounded-[14px] bg-[#f4efe3] py-1.5 pl-2 pr-4', className)} style={style}>
      <Image
        src={ILLUSTRATIONS.homeMood}
        alt=""
        width={190}
        height={200}
        className="v2-anim-image-float w-[79px] shrink-0 select-none"
      />
      <div className="min-w-0">
        <h3 className="text-[13px] font-bold leading-snug text-[var(--v2-ink)]">
          Cek suasana hatimu hari ini
        </h3>
        <p className="mt-0.5 text-[12px] font-medium text-[var(--v2-ink)]">
          Bagaimana perasaanmu sekarang?
        </p>
        <div className="mt-1 flex gap-[7px]">
          {MOODS.map(({ value, label, Icon, color }) => (
            <button
              key={value}
              type="button"
              aria-label={label}
              onClick={() => submitMood.mutate(value)}
              className={cn(
                'v2-anim-pressable grid h-[31px] w-[31px] place-items-center rounded-full border bg-[#fdf9f2]',
                selectedValue === value ? 'border-[var(--v2-olive)] border-2' : 'border-[#e3d6bf]'
              )}
            >
              <Icon className="h-[19px] w-[19px]" strokeWidth={2.2} style={{ color }} />
            </button>
          ))}
        </div>
        <p className="mt-0.5 text-[10px] font-medium text-[var(--v2-ink)]">
          {todayEntry ? 'Sudah tercatat, makasih sudah cerita ke AXIS.' : 'Ini bantu AXIS memahami kamu lebih baik.'}
        </p>
      </div>
      <Image
        src={ILLUSTRATIONS.homeHeart}
        alt=""
        width={110}
        height={105}
        className="v2-anim-image-float absolute bottom-2 right-2 w-[42px] select-none"
      />
    </section>
  );
}

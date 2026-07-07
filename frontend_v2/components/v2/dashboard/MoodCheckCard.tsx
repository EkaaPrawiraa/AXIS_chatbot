'use client';

import Image from 'next/image';
import { Frown, ILLUSTRATIONS, Laugh, Meh, Smile } from '@/lib/assets';
import type { CSSProperties } from 'react';
import { cn } from '@/lib/utils';
import { useMoodTrend, useSubmitMood } from '@/hooks';
import { useSessionStore } from '@/stores';
import { dashboardStyles } from '@/lib/styles/dashboard';

const MOODS = [
  { value: 1, label: 'Sangat sedih', Icon: Frown, color: '#ef4444' }, // Red
  { value: 2, label: 'Sedih', Icon: Frown, color: '#f97316' }, // Orange
  { value: 3, label: 'Biasa saja', Icon: Meh, color: '#eab308' }, // Yellow
  { value: 4, label: 'Cukup baik', Icon: Smile, color: '#84cc16' }, // Lime
  { value: 5, label: 'Senang', Icon: Laugh, color: '#22c55e' }, // Green
];

function todayJakartaDate(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jakarta' });
}

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
    <section className={cn(dashboardStyles.moodCheckContainer, className)} style={style}>
      <div>
        <h2 className={cn(dashboardStyles.sectionHeadingNoMargin, 'mb-2')}>
          Bagaimana perasaanmu hari ini?
        </h2>
        <p className={dashboardStyles.sectionSubtext}>
          {todayEntry ? 'Makasih sudah membagikan perasaanmu' : 'Pilih satu yang paling menggambarkan suasana hatimu hari ini'}
        </p>
      </div>
      <div className={dashboardStyles.moodCheckGrid}>
        {MOODS.map(({ value, label, Icon, color }) => {
          const isSelected = selectedValue === value;
          return (
            <button
              key={value}
              type="button"
              aria-label={label}
              onClick={() => submitMood.mutate(value)}
              disabled={submitMood.isPending}
              className={cn(
                dashboardStyles.moodCheckButtonBase,
                isSelected
                  ? dashboardStyles.moodCheckButtonSelected
                  : dashboardStyles.moodCheckButtonUnselected
              )}
            >
              <Icon
                className={dashboardStyles.moodCheckIcon}
                strokeWidth={isSelected ? 2.5 : 2}
                style={{ color }}
              />
            </button>
          );
        })}
      </div>
      <div className={dashboardStyles.moodCheckScaleLabels}>
        <span>Sedih</span>
        <span>Senang</span>
      </div>
    </section>
  );
}

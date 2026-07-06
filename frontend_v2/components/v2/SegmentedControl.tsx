'use client';

import { cn } from '@/lib/utils';
import { animationClasses } from '@/lib/animations';

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

/**
 * Two-or-more option pill switch (e.g. Masuk / Daftar) matching the
 * axis_mobile_v3 tab style: hairline-bordered cream track, olive active pill.
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}) {
  const activeIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value)
  );

  return (
    <div
      className={cn(
        'relative grid overflow-hidden rounded-[12px] border border-[var(--v2-line)] bg-[#f8f1e5] p-1',
        className
      )}
      style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }}
      role="tablist"
    >
      <span
        aria-hidden="true"
        className={cn(
          'absolute bottom-1 left-1 top-1 rounded-[11px] bg-[var(--v2-olive)] shadow-[0_10px_22px_rgb(83_67_46_/_0.14)]',
          animationClasses.segmentIndicator
        )}
        style={{
          width: `calc((100% - 8px) / ${options.length})`,
          transform: `translateX(${activeIndex * 100}%)`,
        }}
      />
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'relative z-10 h-[42px] rounded-[11px] text-[15px] font-bold transition-colors duration-200',
              active ? 'text-white' : 'text-[var(--v2-ink)]'
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

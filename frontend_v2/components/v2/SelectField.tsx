'use client';

import { ChevronDown } from '@/lib/assets';
import type { ReactNode, SelectHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';


export function SelectField({
  label,
  icon,
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  icon: ReactNode;
}) {
  return (
    <label className={cn('block', className)}>
      <span className="v2-label block">{label}</span>
      <span className="relative mt-1 block">
        <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--v2-olive)]">
          {icon}
        </span>
        <select
          className="v2-field v2-field-lead v2-field-trail appearance-none text-[15px] font-medium"
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-[var(--v2-ink)]" />
      </span>
    </label>
  );
}

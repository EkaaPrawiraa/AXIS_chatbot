'use client';

import type { InputHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';


export function TextField({
  label,
  icon,
  trailing,
  helper,
  className,
  inputClassName,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  icon: ReactNode;
  trailing?: ReactNode;
  helper?: string;
  inputClassName?: string;
}) {
  return (
    <label className={cn('block', className)}>
      <span className="v2-label block">{label}</span>
      <span className="relative mt-1 block">
        <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--v2-olive)]">
          {icon}
        </span>
        <input
          className={cn(
            'v2-field v2-field-lead text-[15px] font-medium',
            trailing && 'v2-field-trail',
            inputClassName
          )}
          {...props}
        />
        {trailing}
      </span>
      {helper ? (
        <span className="mt-1 block px-1 text-[12px] font-medium text-[var(--v2-muted)]">{helper}</span>
      ) : null}
    </label>
  );
}

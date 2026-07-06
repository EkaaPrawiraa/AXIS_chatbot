import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { animationClasses } from '@/lib/animations';

type Variant = 'primary' | 'secondary' | 'ghost' | 'soft' | 'danger';

export function V2Button({
  className,
  variant = 'primary',
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; children: ReactNode }) {
  return (
    <button
      className={cn(
        'v2-button',
        animationClasses.pressable,
        variant === 'primary' && 'v2-button-primary',
        variant === 'secondary' && 'v2-button-secondary',
        variant === 'ghost' && 'v2-button-ghost',
        variant === 'soft' && 'v2-button-soft',
        variant === 'danger' && 'v2-button-danger',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

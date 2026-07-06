import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export function V2Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('v2-card', className)} {...props} />;
}

export function V2SectionTitle({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="space-y-1">
      {eyebrow ? <p className="v2-eyebrow">{eyebrow}</p> : null}
      <h1 className="v2-page-title">{title}</h1>
      {description ? <p className="v2-page-description">{description}</p> : null}
    </div>
  );
}

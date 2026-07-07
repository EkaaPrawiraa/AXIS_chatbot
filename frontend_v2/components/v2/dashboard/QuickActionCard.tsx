import Link from 'next/link';
import type { CSSProperties, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { ChevronRight } from 'lucide-react';
import { dashboardStyles } from '@/lib/styles/dashboard';

export function QuickActionCard({
  href,
  label,
  description,
  icon,
  className,
  style,
}: {
  href: string;
  label: string;
  description?: string;
  icon?: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <Link
      href={href}
      className={cn(dashboardStyles.quickActionCard, className)}
      style={style}
    >
      <div className={dashboardStyles.quickActionContent}>
        {icon && (
          <div className={dashboardStyles.quickActionIconWrapper}>
            {icon}
          </div>
        )}
        <div className={dashboardStyles.quickActionTextWrapper}>
          <span className={dashboardStyles.itemTitle}>
            {label}
          </span>
          {description && (
            <span className={dashboardStyles.itemDescription}>
              {description}
            </span>
          )}
        </div>
      </div>
      <ChevronRight className={dashboardStyles.quickActionChevron} />
    </Link>
  );
}

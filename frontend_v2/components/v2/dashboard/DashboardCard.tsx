'use client';

import type { CSSProperties } from 'react';
import { cn } from '@/lib/utils';
import { ArrowRight, ChevronRight, Sparkles } from 'lucide-react';
import { dashboardStyles } from '@/lib/styles/dashboard';
import Link from 'next/link';

interface DashboardCardProps {
  name: string;
  insight?: {
    title: string;
    body: string;
    conversationId?: string;
  } | null;
  className?: string;
  style?: CSSProperties;
}

export function DashboardCard({
  name,
  insight,
  className,
  style,
}: DashboardCardProps) {
  return (
    <section className={cn(dashboardStyles.dashboardCardContainer, className)} style={style}>
      <div className={dashboardStyles.heroHeaderGroup}>
        <h1 className={dashboardStyles.heroHeading}>
          Haii, {name}
        </h1>
        {insight ? (
          <p className={dashboardStyles.heroSubtext}>
            Ada hal menarik dari percakapan kita sebelumnya,
          </p>
        ) : (
          <div className={dashboardStyles.heroContainer}>
            <p className={dashboardStyles.heroSubtext}>
              Gimana harimu sejauh ini? Boleh ceritakan denganku yaa
            </p>
            <Link
              href="/chat"
              className={dashboardStyles.primaryButton}
              aria-label="Mulai ngobrol"
            >
              <ChevronRight className={dashboardStyles.primaryIcon} strokeWidth={2.5} />
            </Link>
          </div>
        )}
      </div>

      {insight && (
        <div className={dashboardStyles.insightCardContainer}>
          <h3 className={cn(dashboardStyles.insightCardHeader, dashboardStyles.itemTitle)}>
            <span className={dashboardStyles.insightCardTitle}>{insight.title}</span>
          </h3>
          <p className={cn(dashboardStyles.insightCardDescription, dashboardStyles.itemDescription)}>
            {insight.body}
          </p>
          <Link
            href={insight.conversationId ? `/chat?conversationId=${insight.conversationId}` : "/chat"}
            className={dashboardStyles.insightCardLink}
          >
            <span>Lanjut dari sini</span>
            <ArrowRight className={dashboardStyles.insightCardLinkIcon} />
          </Link>
        </div>
      )}
    </section>
  );
}

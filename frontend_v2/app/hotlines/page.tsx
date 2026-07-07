'use client';

import { Heart } from '@/lib/assets';
import { useMemo, useState } from 'react';
import { V2Shell } from '@/components/v2/V2Shell';
import { MobileAppHeader } from '@/components/v2/MobileAppHeader';
import { cn } from '@/lib/utils';
import { hotlineStyles } from '@/lib/styles/hotlineStyles';

import {
  FILTERS,
  RESOURCES,
  type HotlineCategory,
} from '@/lib/hotlinesData';
import { HotlineCard } from '@/components/v2/hotlines/HotlineCard';


export default function HotlinesPage() {
  const [activeFilter, setActiveFilter] = useState<HotlineCategory>('Semua');

  const filteredResources = useMemo(() => {
    return RESOURCES.filter((resource) => {
      return activeFilter === 'Semua' || resource.category === activeFilter;
    });
  }, [activeFilter]);

  return (
    <V2Shell showTopbar={false}>
      <main className={hotlineStyles.pageWrapper}>
        <div className={hotlineStyles.headerContainer}>
          <MobileAppHeader />
        </div>

        <section className={hotlineStyles.pageHeaderWrapper}>
          <h1 className={hotlineStyles.pageTitle}>
            Hotline & Bantuan Darurat
          </h1>
          <p className={hotlineStyles.pageSubtitle}>
            Kamu tidak sendiri. Bantuan selalu ada untukmu.
          </p>
        </section>



        <section className={hotlineStyles.filterScrollWrapper}>
          <button
            type="button"
            onClick={() => setActiveFilter('Semua')}
            className={cn(
              hotlineStyles.filterChipBase,
              activeFilter === 'Semua'
                ? hotlineStyles.filterChipActive
                : hotlineStyles.filterChipInactive
            )}
          >
            Semua
          </button>
          {FILTERS.slice(1).map((filter) => {
            const active = activeFilter === filter;
            return (
              <button
                key={filter}
                type="button"
                onClick={() => setActiveFilter(filter)}
                className={cn(
                  hotlineStyles.filterChipBase,
                  active
                    ? hotlineStyles.filterChipActive
                    : hotlineStyles.filterChipInactive
                )}
              >
                {filter}
              </button>
            );
          })}
        </section>

        <section id="daftar-hotline" className="space-y-3">
          {filteredResources.map((resource) => (
            <HotlineCard key={resource.id} resource={resource} />
          ))}
        </section>

        <section className={hotlineStyles.supportNoteWrapper}>
          <Heart className="h-[22px] w-[22px] shrink-0 text-[#E88DA0]" fill="currentColor" strokeWidth={0} />
          <p className={hotlineStyles.supportNoteText}>
            Semua layanan di atas aman, rahasia, dan gratis. AXIS peduli dan mendukungmu.
          </p>
        </section>
      </main>
    </V2Shell>
  );
}



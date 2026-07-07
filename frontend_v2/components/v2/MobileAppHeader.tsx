'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Avatar from 'boring-avatars';
import { AxisWordmark } from '@/components/v2/AxisMark';
import { CONCEPT_ICONS } from '@/lib/assets';
import { useSessionStore } from '@/stores';

/**
 * Shared mobile header for top-level v2 pages.
 *
 * Used by Beranda, Chat list, Memori, Peta, and Profile so the AXIS wordmark,
 * help/settings affordance, and profile avatar stay visually identical across
 * primary tabs.
 * Chat detail keeps its own ChatHeader because it needs a back action.
 */
export function MobileAppHeader() {
  const pathname = usePathname();
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);
  const isProfile = pathname === '/profile' || pathname?.startsWith('/profile/');
  const isHelp = pathname === '/help' || pathname?.startsWith('/help/');
  const isMemories = pathname === '/memories' || pathname?.startsWith('/memories/');
  const showSettings = isProfile || isHelp;
  const UtilityIcon = isMemories ? CONCEPT_ICONS.knowledgeGraph : showSettings ? CONCEPT_ICONS.pengaturan : CONCEPT_ICONS.bantuan;
  const utilityHref = isMemories ? '/knowledge-graph' : showSettings ? '/settings' : '/help';
  const utilityLabel = isMemories ? 'Peta Relasi Memori' : showSettings ? 'Pengaturan' : 'Bantuan';

  return (
    <header className="flex items-center justify-between">
      <AxisWordmark className="!text-[22px] !tracking-[0.2em]" markSize={30} mark="monogram" />
      <div className="flex items-center gap-3">
        <Link
          href={utilityHref}
          className="relative grid h-10 w-10 place-items-center text-[var(--v2-ink)]"
          aria-label={utilityLabel}
        >
          <UtilityIcon className="h-[23px] w-[23px]" strokeWidth={2.2} />
        </Link>
        <Link href="/profile" aria-label="Profil" className="block overflow-hidden rounded-full">
          <Avatar
            size={38}
            name={user?.id ?? profile?.userId ?? "AXIS User"}
            variant="beam"
            colors={["#F2EFE8", "#D8DDC2", "#84A971", "#E7DFCC", "#F2D8C8"]}
          />
        </Link>
      </div>
    </header>
  );
}

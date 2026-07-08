'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Avatar from 'boring-avatars';
import { AxisWordmark } from '@/components/v2/AxisMark';
import { CONCEPT_ICONS } from '@/lib/assets';
import { cn } from '@/lib/utils';
import { useSessionStore } from '@/stores';


export function MobileAppHeader() {
  const pathname = usePathname();
  const user = useSessionStore((state) => state.user);
  const profile = useSessionStore((state) => state.profile);

  const isProfile = pathname === '/profile' || pathname?.startsWith('/profile/');
  const isHelp = pathname === '/help' || pathname?.startsWith('/help/');
  const isMemories = pathname === '/memories' || pathname?.startsWith('/memories/');
  const isChat = pathname === '/chat' || pathname?.startsWith('/chat/');

  const showSettings = isProfile || isHelp;

  const UtilityIcon = isChat
    ? CONCEPT_ICONS.confession
    : isMemories
      ? CONCEPT_ICONS.knowledgeGraph
      : showSettings
        ? CONCEPT_ICONS.pengaturan
        : CONCEPT_ICONS.bantuan;

  const utilityHref = isChat
    ? '/confession-space'
    : isMemories
      ? '/knowledge-graph'
      : showSettings
        ? '/settings'
        : '/help';

  const utilityLabel = isChat
    ? 'Confession Space'
    : isMemories
      ? 'Peta Relasi Memori'
      : showSettings
        ? 'Pengaturan'
        : 'Bantuan';

  return (
    <header className="v2-mobile-header">
      <div className="v2-mobile-header-inner">
        <Link href="/" className="v2-mobile-header-brand" aria-label="Beranda AXIS">
          <AxisWordmark
            className="v2-mobile-header-wordmark"
            markSize={30}
            mark="monogram"
          />
        </Link>

        <div className="v2-mobile-header-actions">
          <Link
            href={utilityHref}
            className={cn(
              'v2-mobile-header-icon-btn',
              (isMemories || showSettings) && 'is-active'
            )}
            aria-label={utilityLabel}
          >
            <UtilityIcon className="v2-mobile-header-icon" />
          </Link>

          <Link
            href="/profile"
            aria-label="Profil"
            className={cn(
              'v2-mobile-header-avatar-link',
              isProfile && 'is-active'
            )}
          >
            <Avatar
              size={34}
              name={user?.id ?? profile?.userId ?? 'AXIS User'}
              variant="beam"
              colors={['#F2EFE8', '#D8DDC2', '#84A971', '#E7DFCC', '#F2D8C8']}
            />
          </Link>
        </div>
      </div>
    </header>
  );
}
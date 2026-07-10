'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { CONCEPT_ICONS } from '@/lib/assets';
import { cn } from '@/lib/utils';
import { MobileAppHeader } from './MobileAppHeader';
import { SafetyConsentGate } from '@/components/v2/safety/SafetyConsentGate';
import { EvaluationBanner } from '@/components/v2/EvaluationBanner';
import { Snackbar } from '@/components/v2/Snackbar';

const navItems = [
  { href: '/', label: 'Beranda', icon: CONCEPT_ICONS.beranda },
  { href: '/chat', label: 'Chat', icon: CONCEPT_ICONS.chat },
  { href: '/memories', label: 'Memori', icon: CONCEPT_ICONS.memori },
  { href: '/hotlines', label: 'Hotline', icon: CONCEPT_ICONS.hotline },
  { href: '/profile', label: 'Profil', icon: CONCEPT_ICONS.profil },
];

interface V2ShellProps {
  children: React.ReactNode;
  showTopbar?: boolean;
  showBottomNav?: boolean;
}

export function V2Shell({
  children,
  showTopbar = true,
  showBottomNav = true,
}: V2ShellProps) {
  const pathname = usePathname();

  return (
    <div className="v2-app-shell">
      <Snackbar />

      {showTopbar ? <MobileAppHeader /> : null}

      <div className={cn('v2-app-content', showBottomNav && 'v2-app-content--with-bottom-nav')}>
        {/* alert buat ngingetin ini bot evaluasi, jangan diilangin */}
        <EvaluationBanner />
        {children}
      </div>

      {/* gate consent biar ga asal masuk */}
      <SafetyConsentGate />

      {showBottomNav ? (
        <nav className="v2-bottom-nav" aria-label="Navigasi utama">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn('v2-bottom-nav-item', active && 'is-active')}
              >
                <span className="v2-bottom-nav-icon-wrap" aria-hidden="true">
                  <Icon className="v2-bottom-nav-icon" />
                </span>
                <span className="v2-bottom-nav-label">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      ) : null}
    </div>
  );
}

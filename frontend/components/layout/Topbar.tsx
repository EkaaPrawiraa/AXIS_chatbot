'use client';

import { useUIStore, useSessionStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { CircleHelp, LogIn, Menu, Moon, Sun, UserRound, X } from 'lucide-react';
import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useT } from '@/lib/i18n';
import type { ThemeMode } from '@/lib/config/theme';

export function Topbar() {
  const t = useT();
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const mobileNavOpen = useUIStore((state) => state.mobileNavOpen);
  const setMobileNavOpen = useUIStore((state) => state.setMobileNavOpen);
  const setThemeMode = useUIStore((state) => state.setThemeMode);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const user = useSessionStore((state) => state.user);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    setThemeMode(newTheme as ThemeMode);
  };

  const toggleMobileNav = () => {
    setMobileNavOpen(!mobileNavOpen);
  };

  return (
    <header
      className={cn(
        'fixed right-0 top-0 z-30 flex h-16 items-center border-b border-border/80 bg-background/82 px-4 backdrop-blur-xl transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] sm:px-6',
        sidebarCollapsed ? 'left-0 md:left-20' : 'left-0 md:left-72'
      )}
    >
      <div className="flex w-full items-center justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={toggleMobileNav}
            className="md:hidden"
            aria-label={mobileNavOpen ? t('closeNavigation') : t('openNavigation')}
          >
            {mobileNavOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </Button>
          <div className="hidden md:block">
            <h2 className="text-sm font-semibold tracking-[-0.01em]">{t('companionChat')}</h2>
            <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
              {t('topbarTagline')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <>
              <Link href="/profile">
                <Button variant="outline" size="sm" className="gap-2 rounded-full bg-card/80">
                  <UserRound className="w-4 h-4" />
                  <span className="hidden md:inline">{user?.displayName || t('profile')}</span>
                </Button>
              </Link>
            </>
          ) : (
            <Link href="/auth">
              <Button variant="outline" size="sm" className="gap-2 rounded-full bg-card/80">
                <LogIn className="w-4 h-4" />
                <span className="hidden md:inline">{t('signIn')}</span>
              </Button>
            </Link>
          )}

          <Link href="/help">
            <Button variant="ghost" size="icon-sm" className="rounded-full" aria-label={t('openHelp')}>
              <CircleHelp className="w-4 h-4" />
            </Button>
          </Link>

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={toggleTheme}
            className="rounded-full"
            aria-label={mounted && theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {mounted && theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </header>
  );
}

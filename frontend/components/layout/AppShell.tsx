'use client';

import { ReactNode, Suspense } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { EvaluationBanner } from './EvaluationBanner';
import { useSessionStore, useUIStore } from '@/stores';
import { Button } from '@/components/ui/button';
import { useUpdateProfile } from '@/hooks';
import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { usePathname } from 'next/navigation';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const t = useT();
  const pathname = usePathname();
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const mobileNavOpen = useUIStore((state) => state.mobileNavOpen);
  const setMobileNavOpen = useUIStore((state) => state.setMobileNavOpen);
  const userId = useSessionStore((state) => state.userId);
  const profile = useSessionStore((state) => state.profile);
  const setProfile = useSessionStore((state) => state.setProfile);
  const updateProfile = useUpdateProfile();

  const needsSafetyConsent = Boolean(userId && profile && !profile.safetyTermsAccepted);
  const lockContentScroll = pathname === '/chat';

  const acceptSafetyTerms = async () => {
    if (!userId || !profile) return;
    const updated = await updateProfile.mutateAsync({
      userId,
      request: {
        name: profile.name,
        language: profile.language,
        preferredLanguage: profile.language,
        preferredVoiceId: profile.preferredVoiceId,
        preferredTtsModel: profile.preferredTtsModel,
        safetyTermsAccepted: true,
        safetyTermsVersion: 'companion-safety-v1',
      },
    });
    setProfile(updated);
  };

  return (
    <div className="flex min-h-[100dvh] w-full overflow-hidden bg-background text-foreground">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_18%_10%,color-mix(in_oklab,var(--accent)_36%,transparent),transparent_28%),linear-gradient(90deg,color-mix(in_oklab,var(--border)_34%,transparent)_1px,transparent_1px),linear-gradient(180deg,color-mix(in_oklab,var(--border)_34%,transparent)_1px,transparent_1px)] bg-[size:auto,56px_56px,56px_56px] opacity-70" />
      <Suspense fallback={null}>
        <Sidebar />
      </Suspense>

      {mobileNavOpen && (
        <button
          type="button"
          aria-label={t('closeNavigation')}
          className="fixed inset-0 z-30 bg-foreground/18 backdrop-blur-sm md:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <div
        className={cn(
          'flex min-w-0 flex-1 flex-col transition-[margin] duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]',
          sidebarCollapsed ? 'md:ml-20' : 'md:ml-72'
        )}
      >
        <Topbar />

        <main id="main-content" className="relative min-h-0 flex-1 overflow-hidden pt-16">
          <div className="flex h-full min-h-0 flex-col">
            <EvaluationBanner />
            <div className={cn('min-h-0 flex-1', lockContentScroll ? 'overflow-hidden' : 'overflow-y-auto')}>
              {children}
            </div>
            <footer className="border-t border-border/80 bg-background/82 px-6 py-4 text-center font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground backdrop-blur-xl">
              © 2026 Mohammad Nugraha Eka Prawira IF'22 ITB
            </footer>
          </div>
        </main>
      </div>
      {needsSafetyConsent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/88 px-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-[1.35rem] border border-border bg-card p-6 shadow-[var(--axis-shadow)]">
            <p className="axis-eyebrow">
              {t('safetyNoticeEyebrow')}
            </p>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.02em]">{t('safetyNoticeTitle')}</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{t('safetyNoticeDescription')}</p>
            <div className="mt-5 space-y-3 rounded-xl border border-border bg-muted/35 p-4 text-sm leading-6 text-muted-foreground">
              <p>{t('safetyNoticeCan')}</p>
              <p>{t('safetyNoticeCannot')}</p>
              <p>{t('safetyNoticeEmergency')}</p>
            </div>
            <Button
              className="mt-6 w-full"
              onClick={() => void acceptSafetyTerms()}
              disabled={updateProfile.isPending}
            >
              {updateProfile.isPending ? t('saving') : t('agreeAndContinue')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

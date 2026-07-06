'use client';

import { Loader2 } from '@/lib/assets';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';
import { useSessionStore } from '@/stores';

export function AuthRequired({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isInitialized = useSessionStore((state) => state.isInitialized);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (!isInitialized || isAuthenticated) return;
    router.replace(`/auth?next=${encodeURIComponent(pathname || '/chat')}`);
  }, [isAuthenticated, isInitialized, pathname, router]);

  if (!isInitialized) {
    return (
      <main className="v2-screen v2-center">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--v2-olive)]" />
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="v2-screen v2-center">
        <p className="text-sm text-[var(--v2-muted)]">Mengalihkan ke halaman masuk...</p>
      </main>
    );
  }

  return <>{children}</>;
}

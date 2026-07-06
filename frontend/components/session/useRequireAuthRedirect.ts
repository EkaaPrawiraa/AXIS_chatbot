'use client';

import { useSessionStore } from '@/stores';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';

export function useRequireAuthRedirect() {
  const router = useRouter();
  const pathname = usePathname();
  const isInitialized = useSessionStore((state) => state.isInitialized);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (!isInitialized || isAuthenticated) return;
    const next = pathname && pathname !== '/auth' ? `?next=${encodeURIComponent(pathname)}` : '';
    router.replace(`/auth${next}`);
  }, [isAuthenticated, isInitialized, pathname, router]);

  return { isInitialized, isAuthenticated };
}

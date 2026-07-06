'use client';

import { ReactNode, useEffect } from 'react';
import { QueryProvider } from './query-provider';
import { ThemeProvider } from '@/components/theme-provider';
import { SessionInitializer } from '@/components/session';
import { usePreferencesStore } from '@/stores/preferences';

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const hydrateLanguage = usePreferencesStore((state) => state.hydrateLanguage);
  const hydrateChatResponseMode = usePreferencesStore((state) => state.hydrateChatResponseMode);

  useEffect(() => {
    hydrateLanguage();
    hydrateChatResponseMode();
  }, [hydrateLanguage, hydrateChatResponseMode]);

  return (
    <QueryProvider>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <SessionInitializer>{children}</SessionInitializer>
      </ThemeProvider>
    </QueryProvider>
  );
}

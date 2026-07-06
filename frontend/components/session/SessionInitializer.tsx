'use client';

import { ReactNode, useEffect } from 'react';
import { useSessionStore } from '@/stores';

interface SessionInitializerProps {
  children: ReactNode;
}

export function SessionInitializer({ children }: SessionInitializerProps) {
  const initializeSession = useSessionStore((state) => state.initializeSession);

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  return <>{children}</>;
}

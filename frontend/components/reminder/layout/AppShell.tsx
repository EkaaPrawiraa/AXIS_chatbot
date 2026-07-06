'use client';

import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useUIStore } from '@/stores';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);

  return (
    <div className="flex h-[100dvh] w-screen bg-background">
      <Sidebar />

      <div className={`flex flex-1 flex-col transition-all duration-300 ${sidebarCollapsed ? 'ml-16' : 'ml-64'}`}>
        <Topbar />

        <main className="flex-1 overflow-y-auto pt-16">
          <div className="h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

'use client';

import { useUIStore } from '@/stores';
import { useConversations } from '@/hooks';
import { useSessionStore } from '@/stores';
import Link from 'next/link';
import { useState } from 'react';
import { MessageSquare, FileText, LifeBuoy, Settings, Plus, Trash2, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { icon: MessageSquare, label: 'Chat', href: '/chat' },
  { icon: FileText, label: 'Memories', href: '/memories' },
  { icon: LifeBuoy, label: 'Hotlines', href: '/hotlines' },
];

export function Sidebar() {
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const userId = useSessionStore((state) => state.userId);
  
  const { data: conversations = [] } = useConversations(userId);
  const [showAllConversations, setShowAllConversations] = useState(false);

  const displayedConversations = showAllConversations ? conversations : conversations.slice(0, 5);

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-[100dvh] flex-col border-r border-border bg-card transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex items-center justify-between border-b border-border p-4">
        {!sidebarCollapsed && <h1 className="font-semibold text-lg">Companion</h1>}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className="ml-auto"
        >
          <ChevronDown className={cn('w-4 h-4 transition-transform', sidebarCollapsed && 'rotate-90')} />
        </Button>
      </div>

      {!sidebarCollapsed && (
        <Link href="/chat" className="p-4">
          <Button className="w-full justify-start">
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </Link>
      )}

      <nav className="flex-1 space-y-2 overflow-y-auto p-4">
        {NAV_ITEMS.map((item) => (
          <Link key={item.href} href={item.href}>
            <Button
              variant="ghost"
              className={cn(
                'w-full justify-start',
                sidebarCollapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="w-4 h-4" />
              {!sidebarCollapsed && <span className="ml-2">{item.label}</span>}
            </Button>
          </Link>
        ))}

        {!sidebarCollapsed && conversations.length > 0 && (
          <div className="mt-4 border-t border-border pt-4">
            <h3 className="mb-2 px-2 font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Recent Chats
            </h3>
            <div className="space-y-1">
              {displayedConversations.map((conversation) => (
                <Link key={conversation.id} href={`/chat/${conversation.id}`}>
                  <Button variant="ghost" className="w-full justify-start text-sm truncate">
                    {conversation.title}
                  </Button>
                </Link>
              ))}
            </div>

            {conversations.length > 5 && (
              <Button
                variant="ghost"
                className="w-full justify-start text-xs mt-2"
                onClick={() => setShowAllConversations(!showAllConversations)}
              >
                {showAllConversations ? 'Show Less' : `Show All (${conversations.length})`}
              </Button>
            )}
          </div>
        )}
      </nav>

      <div className="border-t border-border p-4">
        <Link href="/settings" className="w-full">
          <Button variant="ghost" className={cn('w-full justify-start', sidebarCollapsed && 'justify-center')}>
            <Settings className="w-4 h-4" />
            {!sidebarCollapsed && <span className="ml-2">Settings</span>}
          </Button>
        </Link>
      </div>
    </aside>
  );
}

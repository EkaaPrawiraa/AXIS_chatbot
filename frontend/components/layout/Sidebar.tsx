'use client';

import { useChatStore, useSessionStore, useUIStore } from '@/stores';
import { useConversations, useDeleteConversation } from '@/hooks';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
  ChevronDown,
  ChevronUp,
  ClipboardList,
  FileText,
  LifeBuoy,
  MessageSquare,
  Mic,
  Network,
  Plus,
  Settings,
  Trash2,
  X,
} from 'lucide-react';
import { AxisIcon } from '@/components/icons';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Conversation } from '@/models';
import { useT } from '@/lib/i18n';

export function Sidebar() {
  const t = useT();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const sidebarCollapsed = useUIStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const mobileNavOpen = useUIStore((state) => state.mobileNavOpen);
  const setMobileNavOpen = useUIStore((state) => state.setMobileNavOpen);
  const userId = useSessionStore((state) => state.userId);
  const activeConversationId = useChatStore((state) => state.activeConversationId);
  const setActiveConversationId = useChatStore((state) => state.setActiveConversationId);
  const { data: conversations = [], isLoading } = useConversations(userId);
  const deleteConversation = useDeleteConversation();
  const [showAllConversations, setShowAllConversations] = useState(false);
  const [sessionsHidden, setSessionsHidden] = useState(false);
  const evaluationFormUrl = process.env.NEXT_PUBLIC_EVALUATION_FORM_URL;

  const routeConversationId = searchParams.get('id');
  const selectedConversationId = routeConversationId || activeConversationId;
  const displayedConversations = useMemo(
    () => (showAllConversations ? conversations : conversations.slice(0, 10)),
    [conversations, showAllConversations]
  );
  const navItems = [
    { icon: MessageSquare, label: t('chat'), href: '/chat' },
    { icon: Mic, label: t('voiceRoom'), href: '/voice-room' },
    { icon: FileText, label: t('memories'), href: '/memories' },
    { icon: Network, label: t('knowledgeGraph'), href: '/knowledge-graph' },
    { icon: LifeBuoy, label: t('hotlines'), href: '/hotlines' },
  ];

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMobileNavOpen(false);
    router.push('/chat');
  };

  const handleDeleteConversation = async (conversationId: string) => {
    await deleteConversation.mutateAsync(conversationId);
    if (selectedConversationId === conversationId) {
      setActiveConversationId(null);
      router.push('/chat');
    }
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 flex h-[100dvh] flex-col border-r border-sidebar-border bg-sidebar/95 text-sidebar-foreground shadow-[18px_0_60px_rgba(40,35,28,0.06)] backdrop-blur-xl transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
        sidebarCollapsed ? 'md:w-20' : 'md:w-72',
        mobileNavOpen ? 'w-72 translate-x-0' : 'w-72 -translate-x-full md:translate-x-0'
      )}
    >
      <div className="flex items-center justify-between border-b border-sidebar-border/85 p-4">
        <Link
          href="/"
          onClick={() => setMobileNavOpen(false)}
          className={cn(
            'flex items-center gap-3 rounded-xl text-lg font-semibold tracking-[-0.03em] transition-colors hover:text-sidebar-foreground/75',
            sidebarCollapsed && 'md:hidden'
          )}
        >
          <span className="flex size-10 items-center justify-center rounded-xl text-sidebar-accent-foreground">
            <AxisIcon size={36} variant="filled" />
          </span>
          <span>{t('appName')}</span>
        </Link>
        {/* Desktop: collapse toggle */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleSidebar}
          className="ml-auto hidden md:inline-flex"
        >
          <ChevronDown className={cn('w-4 h-4 transition-transform', sidebarCollapsed && 'rotate-90')} />
        </Button>
        {/* Mobile: close button */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setMobileNavOpen(false)}
          className="ml-auto md:hidden"
          aria-label="Tutup menu"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Full-width button: always visible on mobile, hidden on desktop when collapsed */}
      <div className={cn('p-4', sidebarCollapsed && 'md:hidden')}>
        <Button onClick={handleNewChat} className="w-full justify-start rounded-xl">
          <Plus className="w-4 h-4 mr-2" />
          {t('newChat')}
        </Button>
      </div>
      {/* Icon-only button: only on desktop when collapsed */}
      {sidebarCollapsed && (
        <div className="hidden p-3 md:block">
          <Button onClick={handleNewChat} size="icon" className="w-12 rounded-xl">
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      )}

      <nav className="space-y-1 px-3">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href} onClick={() => setMobileNavOpen(false)}>
            <Button
              variant="ghost"
              className={cn(
                'h-11 w-full justify-start rounded-xl text-sidebar-foreground/72 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                pathname === item.href && 'bg-sidebar-accent text-sidebar-accent-foreground',
                sidebarCollapsed && 'md:justify-center md:px-2'
              )}
            >
              <item.icon className="w-4 h-4" />
              <span className={cn('ml-2', sidebarCollapsed && 'md:hidden')}>{item.label}</span>
            </Button>
          </Link>
        ))}
      </nav>

      <section className={cn('mt-4 flex min-h-[8rem] min-w-0 flex-1 flex-col overflow-hidden border-t border-sidebar-border/85 px-4 pt-4', sidebarCollapsed && 'md:hidden')}>
          <div className="mb-2 flex items-center justify-between px-1">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sidebar-foreground/50">{t('sessions')}</h3>
            {userId && (
              <button
                type="button"
                onClick={() => setSessionsHidden((prev) => !prev)}
                className="group/sess-toggle relative inline-flex h-6 items-center gap-1.5 rounded-md px-1.5 text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent/70 hover:text-sidebar-foreground"
                aria-label={sessionsHidden ? t('showAll', conversations.length) : t('hide')}
                title={String(conversations.length)}
              >
                <span className="font-mono text-[10px] font-semibold tabular-nums opacity-0 transition-opacity group-hover/sess-toggle:opacity-100">
                  {conversations.length}
                </span>
                {sessionsHidden ? (
                  <ChevronUp className="size-3.5" />
                ) : (
                  <ChevronDown className="size-3.5" />
                )}
              </button>
            )}
          </div>

          {!userId ? (
            <div className="rounded-xl border border-dashed border-sidebar-border px-3 py-4 text-sm leading-6 text-sidebar-foreground/62">
              {t('loginForSessions')}
            </div>
          ) : isLoading ? (
            <SessionSkeleton />
          ) : conversations.length === 0 ? (
            <div className="rounded-xl border border-dashed border-sidebar-border px-3 py-4 text-sm leading-6 text-sidebar-foreground/62">
              {t('noSessionsSidebar')}
            </div>
          ) : sessionsHidden ? null : (
            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
              <div className="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain pr-1 [scrollbar-gutter:stable]">
                <div className="grid w-full min-w-0 gap-1 pb-3">
                  {displayedConversations.map((conversation) => (
                    <SessionRow
                      key={conversation.id}
                      conversation={conversation}
                      isActive={selectedConversationId === conversation.id}
                      isDeleting={deleteConversation.isPending}
                      onOpen={() => {
                        setActiveConversationId(conversation.id);
                        router.push(`/chat?id=${conversation.id}`);
                      }}
                      onDelete={() => handleDeleteConversation(conversation.id)}
                    />
                  ))}
                </div>
              </div>

              {conversations.length > 10 && (
                <Button
                  variant="ghost"
                  className="mt-2 h-8 w-full shrink-0 justify-center text-xs"
                  onClick={() => setShowAllConversations(!showAllConversations)}
                >
                  {showAllConversations ? t('showFewer') : t('showAll', conversations.length)}
                </Button>
              )}
            </div>
          )}
      </section>

      <div className="border-t border-sidebar-border/85 p-4 space-y-1">
        {evaluationFormUrl && evaluationFormUrl !== 'https://forms.gle/REPLACE_ME' && (
          <a href={evaluationFormUrl} target="_blank" rel="noopener noreferrer" className="block w-full">
            <Button
              variant="ghost"
              className={cn(
                'w-full justify-start rounded-xl text-sidebar-foreground/72 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                sidebarCollapsed && 'md:justify-center md:px-2'
              )}
            >
              <ClipboardList className="w-4 h-4" />
              <span className={cn('ml-2', sidebarCollapsed && 'md:hidden')}>{t('questionnaire')}</span>
            </Button>
          </a>
        )}
        <Link href="/settings" className="w-full" onClick={() => setMobileNavOpen(false)}>
          <Button
            variant="ghost"
            className={cn(
              'w-full justify-start rounded-xl text-sidebar-foreground/72 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              pathname === '/settings' && 'bg-sidebar-accent text-sidebar-accent-foreground',
              sidebarCollapsed && 'md:justify-center md:px-2'
            )}
          >
            <Settings className="w-4 h-4" />
            <span className={cn('ml-2', sidebarCollapsed && 'md:hidden')}>{t('settings')}</span>
          </Button>
        </Link>
      </div>
    </aside>
  );
}

function SessionRow({
  conversation,
  isActive,
  isDeleting,
  onOpen,
  onDelete,
}: {
  conversation: Conversation;
  isActive: boolean;
  isDeleting: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const t = useT();
  const label = conversation.title || t('newConversation');
  const preview = (conversation.preview || t('messages', conversation.messageCount || 0)).replace(/\s+/g, ' ').trim();

  return (
    <div
      className={cn(
        'group relative box-border w-full max-w-full min-w-0 overflow-hidden rounded-xl border px-3 py-2.5 transition-[border-color,background-color,box-shadow] duration-200',
        isActive
          ? 'border-sidebar-border bg-sidebar-accent text-sidebar-accent-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.18)]'
          : 'border-transparent hover:border-sidebar-border/70 hover:bg-sidebar-accent/65'
      )}
    >
      <button
        type="button"
        onClick={onOpen}
        className="block w-full max-w-full min-w-0 overflow-hidden pr-7 text-left"
        title={`${label}${preview ? ` - ${preview}` : ''}`}
      >
        <p className="block w-full max-w-full truncate text-sm font-medium leading-5 tracking-normal">
          {label}
        </p>
        <p className="mt-1 block w-full max-w-full truncate text-xs font-normal leading-4 tracking-normal text-sidebar-foreground/58">
          {preview}
        </p>
      </button>

      <Button
        variant="ghost"
        size="sm"
        disabled={isDeleting}
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDelete();
        }}
        className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0 text-sidebar-foreground/45 opacity-0 shadow-sm transition-[opacity,background-color,color] hover:bg-background/80 hover:text-destructive group-hover:opacity-100 focus-visible:opacity-100"
        title={t('deleteSession')}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function SessionSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="rounded-xl px-2 py-2">
          <div className="h-4 w-4/5 animate-pulse rounded bg-sidebar-accent" />
          <div className="mt-2 h-3 w-1/2 animate-pulse rounded bg-sidebar-accent" />
        </div>
      ))}
    </div>
  );
}

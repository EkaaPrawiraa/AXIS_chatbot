'use client';

import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { useT, type TranslationKey } from '@/lib/i18n';
import Link from 'next/link';
import {
  BookOpenText,
  ClipboardCheck,
  FileText,
  HeartHandshake,
  LifeBuoy,
  MessageSquare,
  Mic,
  Network,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react';

type Topic = {
  id: string;
  icon: typeof MessageSquare;
  titleKey: TranslationKey;
  bodyKey: TranslationKey;
  linkHref?: string;
  linkLabelKey?: TranslationKey;
};

const TOPICS: Topic[] = [
  { id: 'chat', icon: MessageSquare, titleKey: 'helpChatTitle', bodyKey: 'helpChatBody', linkHref: '/chat', linkLabelKey: 'helpGoToChat' },
  { id: 'cbt', icon: Sparkles, titleKey: 'helpCbtTitle', bodyKey: 'helpCbtBody' },
  { id: 'phq9', icon: ClipboardCheck, titleKey: 'helpPhq9Title', bodyKey: 'helpPhq9Body' },
  { id: 'voice', icon: Mic, titleKey: 'helpVoiceTitle', bodyKey: 'helpVoiceBody', linkHref: '/voice-room', linkLabelKey: 'helpGoToVoice' },
  { id: 'memories', icon: FileText, titleKey: 'helpMemoriesTitle', bodyKey: 'helpMemoriesBody', linkHref: '/memories', linkLabelKey: 'helpGoToMemories' },
  { id: 'graph', icon: Network, titleKey: 'helpGraphTitle', bodyKey: 'helpGraphBody', linkHref: '/knowledge-graph', linkLabelKey: 'helpGoToGraph' },
  { id: 'safety', icon: ShieldCheck, titleKey: 'helpSafetyTitle', bodyKey: 'helpSafetyBody', linkHref: '/hotlines', linkLabelKey: 'helpGoToHotlines' },
  { id: 'profile', icon: UserRound, titleKey: 'helpProfileTitle', bodyKey: 'helpProfileBody', linkHref: '/profile', linkLabelKey: 'helpGoToProfile' },
];

export default function HelpPage() {
  const t = useT();

  return (
    <AppShell>
      <div className="axis-page">
        <section className="flex flex-col gap-5 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              {t('helpEyebrow')}
            </p>
            <h1 className="mt-3 text-4xl font-semibold leading-none tracking-[-0.05em] sm:text-5xl">
              {t('helpTitle')}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
              {t('helpDescription')}
            </p>
          </div>
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl border border-border bg-card text-primary">
            <BookOpenText className="size-5" />
          </div>
        </section>

        <section className="mt-6 rounded-xl border border-border bg-card shadow-[var(--axis-shadow-soft)]">
          <Accordion type="single" collapsible defaultValue="chat" className="px-4 sm:px-5">
            {TOPICS.map((topic) => {
              const Icon = topic.icon;
              return (
                <AccordionItem key={topic.id} value={topic.id}>
                  <AccordionTrigger className="gap-3 text-base">
                    <span className="flex items-center gap-3">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/30 text-primary">
                        <Icon className="size-4" />
                      </span>
                      <span className="font-semibold tracking-[-0.01em]">{t(topic.titleKey)}</span>
                    </span>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="pl-11">
                      <p className="text-sm leading-7 text-muted-foreground whitespace-pre-line">
                        {t(topic.bodyKey)}
                      </p>
                      {topic.linkHref && topic.linkLabelKey && (
                        <Link href={topic.linkHref} className="mt-3 inline-block">
                          <Button variant="outline" size="sm" className="gap-2 bg-card">
                            {t(topic.linkLabelKey)}
                          </Button>
                        </Link>
                      )}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
        </section>

        <section className="mt-6 rounded-xl border border-destructive/25 bg-destructive/8 p-4 shadow-[var(--axis-shadow-soft)] sm:p-5">
          <div className="flex gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-full border border-destructive/25 bg-background/65 text-destructive">
              <LifeBuoy className="size-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold tracking-[-0.02em]">{t('helpCrisisTitle')}</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{t('helpCrisisBody')}</p>
              <Link href="/hotlines" className="mt-3 inline-block">
                <Button size="sm" className="gap-2">
                  <HeartHandshake className="size-4" />
                  {t('helpGoToHotlines')}
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

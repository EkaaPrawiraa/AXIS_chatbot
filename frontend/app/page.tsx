'use client';

import { AppShell } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { useT } from '@/lib/i18n';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import Link from 'next/link';
import {
  ArrowRight,
  ArrowUpRight,
  GraduationCap,
  MessageSquare,
  Network,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

const smoothEase = [0.22, 1, 0.36, 1] as const;

const pageMotion: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.03,
    },
  },
};

const itemMotion: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.55,
      ease: smoothEase,
    },
  },
};

export default function HomePage() {
  const t = useT();
  const thesisFacts = [
    [t('dashboardAuthorLabel'), 'Mohammad Nugraha Eka Prawira'],
    [t('dashboardStudentIdLabel'), '13522001'],
    [t('dashboardProgramLabel'), 'Teknik Informatika ITB 2022'],
    [t('dashboardSupervisorLabel'), 'Dr. Agung Dewandaru, S.T., M.Sc.'],
  ];
  const systemNotes = [
    [t('dashboardModeLabel'), t('dashboardModeValue')],
    [t('dashboardMemoryLabel'), t('dashboardMemoryValue')],
    [t('dashboardInputLabel'), t('dashboardInputValue')],
    [t('dashboardControlLabel'), t('dashboardControlValue')],
  ];
  const safetyNotes = [t('safetyNoticeCan'), t('safetyNoticeCannot'), t('safetyNoticeEmergency')];

  return (
    <AppShell>
      <motion.div
        className="mx-auto flex w-full max-w-[1480px] flex-col gap-5 px-4 py-4 sm:px-6 lg:px-8 lg:py-7"
        variants={pageMotion}
        initial="hidden"
        animate="show"
      >
        <motion.section
          variants={itemMotion}
          className="relative isolate overflow-hidden rounded-[1.75rem] border border-border/80 bg-card shadow-[var(--axis-shadow)]"
        >
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_80%_8%,color-mix(in_oklab,var(--accent)_48%,transparent),transparent_32%),linear-gradient(135deg,color-mix(in_oklab,var(--axis-wash)_68%,transparent),transparent_42%)]" />
          <div className="pointer-events-none absolute right-[-8rem] top-[-12rem] -z-10 h-80 w-80 rounded-full border border-foreground/8" />
          <div className="grid min-h-[34rem] gap-0 lg:grid-cols-[minmax(0,1.05fr)_minmax(23rem,0.65fr)]">
            <div className="flex flex-col justify-between gap-12 p-5 sm:p-7 lg:p-10">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="axis-kicker rounded-full border-foreground/10 bg-background/70">
                  <Sparkles className="size-3.5 text-accent-foreground" />
                  {t('dashboardEyebrow')}
                </div>
                <Button asChild size="sm" className="rounded-full px-4">
                  <Link href="/chat">
                    {t('dashboardStartChat')}
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>

              <div className="max-w-5xl">
                <p className="mb-5 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  AXIS / {t('dashboardModeValue')}
                </p>
                <h1 className="max-w-[23ch] text-balance text-[clamp(2.75rem,5.1vw,4.9rem)] font-semibold leading-[0.9] tracking-[-0.065em] text-foreground lg:max-w-[24ch]">
                  {t('dashboardCompanionTagline')}
                </h1>
                <p className="mt-7 max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
                  {t('dashboardDescription')}
                </p>
              </div>

              <div className="grid gap-2 border-t border-border/80 pt-4 sm:grid-cols-2 xl:grid-cols-4">
                {systemNotes.map(([label, value]) => (
                  <div key={label} className="min-w-0 rounded-xl bg-background/50 px-3 py-3">
                    <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      {label}
                    </p>
                    <p className="mt-2 truncate text-sm font-semibold text-foreground">{value}</p>
                  </div>
                ))}
              </div>
            </div>

            <aside className="relative flex min-h-[26rem] flex-col justify-between overflow-hidden border-t border-border/80 bg-[#171914] p-5 text-[#f8f4e8] sm:p-7 lg:border-l lg:border-t-0 lg:p-8">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(177,196,139,0.24),transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.08),transparent_45%)]" />
              <div className="relative">
                <div className="flex items-center justify-between gap-4">
                  <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#c9c2ae]">
                    {t('dashboardProfileLabel')}
                  </p>
                  <MessageSquare className="size-5 text-[#d8e2b9]" />
                </div>
                <h2 className="mt-8 max-w-sm break-words text-4xl font-semibold leading-[0.95] tracking-[-0.055em]">
                  {t('dashboardStartChat')}
                </h2>
                <p className="mt-4 max-w-sm text-sm leading-7 text-[#c9c2ae]">{t('dashboardFeatureChatDescription')}</p>
              </div>

              <div className="relative mt-10 space-y-3">
                <Link
                  href="/chat"
                  className="group flex items-center justify-between rounded-2xl bg-[#f8f4e8] px-4 py-3.5 text-sm font-semibold text-[#171914] shadow-[0_18px_42px_rgba(0,0,0,0.2)] transition-transform duration-300 hover:-translate-y-0.5 active:translate-y-0"
                >
                  {t('dashboardFeatureChatTitle')}
                  <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                  <Link
                    href="/memories"
                    className="group rounded-2xl border border-white/10 bg-white/[0.07] p-4 text-sm font-medium text-[#f8f4e8] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition-[background-color,transform] duration-300 hover:-translate-y-0.5 hover:bg-white/[0.11] active:translate-y-0"
                  >
                    <span className="flex items-center justify-between gap-3">
                      {t('dashboardViewMemories')}
                      <ArrowUpRight className="size-4 text-[#c9c2ae] transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </span>
                  </Link>
                  <Link
                    href="/knowledge-graph"
                    className="group rounded-2xl border border-white/10 bg-white/[0.07] p-4 text-sm font-medium text-[#f8f4e8] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition-[background-color,transform] duration-300 hover:-translate-y-0.5 hover:bg-white/[0.11] active:translate-y-0"
                  >
                    <span className="flex items-center justify-between gap-3">
                      {t('knowledgeGraphTitle')}
                      <ArrowUpRight className="size-4 text-[#c9c2ae] transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </span>
                  </Link>
                </div>
              </div>
            </aside>
          </div>
        </motion.section>

        <motion.section variants={itemMotion} className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_27rem]">
          <div className="relative isolate overflow-hidden rounded-[1.35rem] border border-border bg-card p-5 shadow-[var(--axis-shadow-soft)] md:p-7">
            <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_8%_10%,color-mix(in_oklab,var(--accent)_32%,transparent),transparent_30%)]" />
            <div className="flex flex-col justify-between gap-12">
              <div>
                <div className="axis-eyebrow">
                  <ShieldCheck className="size-4 text-accent-foreground" />
                  {t('safetyNoticeEyebrow')}
                </div>
                <h2 className="mt-6 max-w-3xl text-3xl font-semibold leading-[1.02] tracking-[-0.05em] md:text-5xl">
                  {t('safetyNoticeTitle')}
                </h2>
                <p className="mt-5 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
                  {t('safetyNoticeDescription')}
                </p>
              </div>

              <div className="grid gap-3 lg:grid-cols-3">
                {safetyNotes.map((note) => (
                  <div key={note} className="rounded-2xl border border-border bg-background/50 p-4">
                    <p className="text-sm leading-7 text-muted-foreground">{note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <aside>
            <div className="rounded-[1.35rem] border border-border bg-muted/35 p-5 md:p-6">
              <div className="mb-5 flex items-center justify-between gap-4">
                <div className="axis-eyebrow">
                  <GraduationCap className="size-4 text-accent-foreground" />
                  {t('dashboardThesisEyebrow')}
                </div>
                <Network className="size-5 text-muted-foreground" />
              </div>
              <h2 className="text-2xl font-semibold leading-[1.05] tracking-[-0.045em]">{t('dashboardThesisTitle')}</h2>
              <p className="mt-4 text-sm leading-7 text-muted-foreground">{t('dashboardThesisDescription')}</p>
              <div className="mt-6 grid gap-3">
                {thesisFacts.map(([label, value]) => (
                  <div key={label} className="grid gap-1 border-t border-border pt-3 first:border-t-0 first:pt-0">
                    <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      {label}
                    </p>
                    <p className="text-sm font-medium leading-6">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </motion.section>
      </motion.div>
    </AppShell>
  );
}

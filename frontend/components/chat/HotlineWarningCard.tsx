'use client';

import Link from 'next/link';
import { Info } from 'lucide-react';
import { useT } from '@/lib/i18n';

const CRISIS_HOTLINES = [
  {
    id: 'healing119',
    name: 'Healing119.id Hotline',
    contact: '119',
    href: 'tel:119',
  },
  {
    id: 'lisa',
    name: 'LISA Suicide Prevention Helpline',
    contact: '+62 811 3855 472',
    href: 'https://wa.me/628113855472',
  },
] as const;

export function HotlineWarningCard() {
  const t = useT();

  return (
    <div className="mt-3 w-full max-w-3xl rounded-xl border border-border bg-muted/30 px-4 py-4 sm:px-5">
      <div className="flex items-start gap-3">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-background text-foreground">
          <Info className="size-3.5" />
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-sm font-semibold leading-5 tracking-[-0.01em]">{t('crisisWarningTitle')}</p>

          {CRISIS_HOTLINES.map((hotline) => (
            <p key={hotline.id} className="text-sm leading-6 text-muted-foreground">
              {t('crisisCardIfYouNeedHelp')}{' '}
              <a
                href={hotline.href}
                target={hotline.href.startsWith('http') ? '_blank' : undefined}
                rel="noreferrer"
                className="font-medium text-foreground underline decoration-border underline-offset-4 transition-colors hover:decoration-foreground"
              >
                {t('crisisCardCall')} {hotline.contact}
              </a>{' '}
              {t('crisisCardToConnect')}{' '}
              <strong className="font-semibold text-foreground">{hotline.name}</strong>.{' '}
              {t('crisisCardFreeConfidential')}
            </p>
          ))}

          <p className="text-xs text-muted-foreground/70">
            {t('crisisCardDisclaimer')}{' '}
            <Link href="/hotlines" className="underline decoration-border underline-offset-4 hover:text-muted-foreground">
              {t('crisisViewAllHotlines')}
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { X, ClipboardList } from 'lucide-react';
import { useT } from '@/lib/i18n';

const STORAGE_KEY = 'axis_eval_banner_dismissed';
const FORM_URL = process.env.NEXT_PUBLIC_EVALUATION_FORM_URL;

export function EvaluationBanner() {
  const t = useT();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!FORM_URL || FORM_URL === 'https://forms.gle/REPLACE_ME') return;
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) setVisible(true);
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="banner"
      className="flex items-center gap-3 border-b border-border/80 bg-primary/8 px-4 py-2.5 text-sm sm:px-6"
    >
      <ClipboardList className="size-4 shrink-0 text-primary" />
      <p className="min-w-0 flex-1 text-foreground/85">
        {t('evaluationBannerText')}{' '}
        <a
          href={FORM_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-primary underline underline-offset-2 hover:no-underline"
        >
          {t('evaluationBannerLink')}
        </a>
      </p>
      <button
        type="button"
        aria-label={t('close')}
        onClick={dismiss}
        className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}

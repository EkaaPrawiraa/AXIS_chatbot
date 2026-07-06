'use client';

import { ClipboardList, X } from '@/lib/assets';
import { useEffect, useState } from 'react';
import { evaluationFormUrl } from '@/lib/evaluationForm';

const DISMISS_KEY = 'axis-eval-banner-dismissed';

/**
 * Nudges users to fill the TA evaluation questionnaire. Mirrors the original
 * frontend's EvaluationBanner: shown on every page until dismissed, and the
 * dismissal is permanent (localStorage, not per-session) since re-nagging a
 * user who already closed it once would be annoying, not helpful.
 */
export function EvaluationBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem(DISMISS_KEY) === '1';
    if (!dismissed) setVisible(true);
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, '1');
    setVisible(false);
  };

  return (
    <div
      role="banner"
      className="mb-3 flex items-center gap-2.5 rounded-[18px] border border-[var(--v2-line)] bg-[var(--v2-olive-soft)] px-4 py-2.5"
    >
      <ClipboardList className="h-4 w-4 shrink-0 text-[var(--v2-olive-deep)]" strokeWidth={2.2} />
      <p className="min-w-0 flex-1 text-[12.5px] leading-snug text-[var(--v2-ink)]">
        Kamu sedang membantu evaluasi AXIS.{' '}
        <a
          href={evaluationFormUrl}
          target="_blank"
          rel="noreferrer"
          className="font-bold text-[var(--v2-olive-deep)] underline underline-offset-2"
        >
          Isi kuesioner →
        </a>
      </p>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Tutup"
        className="v2-anim-pressable shrink-0 rounded-full p-1 text-[var(--v2-olive-deep)]"
      >
        <X className="h-3.5 w-3.5" strokeWidth={2.3} />
      </button>
    </div>
  );
}

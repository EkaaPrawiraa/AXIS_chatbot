'use client';

import Link from 'next/link';
import { Check, ChevronRight, HeartHandshake, Lock, PhoneCall, ShieldCheck, Sprout } from '@/lib/assets';
import { useState } from 'react';
import { animationClasses } from '@/lib/animations';

/**
 * "Sebelum lanjut" safety consent bottom sheet per the v3 design
 * (13_safety_consent_modal_compact). Shown to users who have not yet
 * accepted the safety terms; "Saya paham" is enabled only after the
 * consent checkbox is ticked.
 */
export function SafetyConsentSheet({
  onAccept,
  onLater,
  isBusy = false,
}: {
  onAccept: () => void;
  onLater: () => void;
  isBusy?: boolean;
}) {
  const [agreed, setAgreed] = useState(false);

  return (
    <div className={`fixed inset-0 z-[85] bg-black/45 ${animationClasses.sheetBackdropIn}`}>
      <aside className={`absolute inset-x-0 bottom-0 mx-auto max-h-[92dvh] w-[min(100%,540px)] overflow-y-auto rounded-t-[28px] bg-[var(--v2-c-f9f2e9)] px-4 pb-4 pt-2 shadow-2xl ${animationClasses.sheetUp}`}>
        <span className="mx-auto block h-[4px] w-12 rounded-full bg-[var(--v2-line-border)]" aria-hidden />

        <div className="mt-2.5 flex items-center gap-2.5">
          <span className="grid h-[40px] w-[40px] shrink-0 place-items-center rounded-full bg-[var(--v2-bg-light-5)]">
            <ShieldCheck className="h-[20px] w-[20px] text-[var(--v2-clay-accent)]" />
          </span>
          <div>
            <h2 className="text-[19px] font-bold leading-tight text-[var(--v2-ink)]">Sebelum lanjut</h2>
            <p className="text-[12.5px] font-medium text-[var(--v2-muted-tertiary)]">Ruang aman bersama AXIS</p>
          </div>
        </div>

        <div className="mt-2.5 flex flex-col">
          <div className="flex items-start gap-3 py-2.5">
            <Sprout className="h-[22px] w-[22px] shrink-0 text-[var(--v2-green-light)]" strokeWidth={2.1} />
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-bold leading-snug text-[var(--v2-ink)]">
                AXIS adalah teman, bukan layanan darurat.
              </p>
              <p className="mt-0.5 text-[11.5px] font-medium leading-snug text-[var(--v2-muted-tertiary)]">
                Aplikasi ini hadir untuk teman refleksi dan dukungan, bukan untuk situasi darurat.
              </p>
            </div>
          </div>
          
          <hr className="my-1 border-[var(--v2-line-lighter)]" />

          <div className="flex items-start gap-3 py-2.5">
            <span className="relative shrink-0">
              <PhoneCall className="h-[22px] w-[22px] text-[var(--v2-green-secondary)]" strokeWidth={2.1} />
              <span className="absolute -right-1 -top-1 grid h-[13px] w-[13px] place-items-center rounded-full bg-[var(--v2-clay-accent)] text-[9px] font-black text-white">
                +
              </span>
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-bold leading-snug text-[var(--v2-ink)]">
                Jika kamu dalam bahaya sekarang,
              </p>
              <p className="mt-0.5 text-[11.5px] font-medium leading-snug text-[var(--v2-muted-tertiary)]">
                segera hubungi hotline atau orang terdekat di sekitarmu.
              </p>
              <Link
                href="/hotlines"
                className="mt-1 flex items-center justify-end gap-0.5 text-[12.5px] font-bold text-[var(--v2-green-secondary)]"
              >
                Lihat hotline <ChevronRight className="h-[14px] w-[14px]" />
              </Link>
            </div>
          </div>

          <hr className="my-1 border-[var(--v2-line-lighter)]" />

          <div className="flex items-start gap-3 py-2.5">
            <HeartHandshake className="h-[22px] w-[22px] shrink-0 text-[var(--v2-clay-accent)]" strokeWidth={2.1} />
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-bold leading-snug text-[var(--v2-ink)]">
                Keselamatanmu lebih penting.
              </p>
              <p className="mt-0.5 text-[11.5px] font-medium leading-snug text-[var(--v2-muted-tertiary)]">
                Kalau merasa tidak aman atau tertekan, berhenti dulu. Kamu berhak untuk aman.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={() => setAgreed((value) => !value)}
          className="mt-2.5 flex items-center gap-2.5 px-1 text-left"
        >
          <span
            className={`grid h-[20px] w-[20px] shrink-0 place-items-center rounded-[6px] border-[1.5px] ${
              agreed ? 'border-[var(--v2-olive)] bg-[var(--v2-olive)] text-white' : 'border-[var(--v2-c-b7ae99)] bg-transparent'
            }`}
          >
            {agreed ? <Check className="h-[13px] w-[13px]" strokeWidth={3} /> : null}
          </span>
          <span className="text-[13.5px] font-semibold text-[var(--v2-ink)]">
            Saya paham dan setuju <span className="text-[var(--v2-c-c04f2f)]">*</span>
          </span>
        </button>

        <button
          onClick={onAccept}
          disabled={!agreed || isBusy}
          className="v2-anim-pressable mt-2.5 h-[46px] w-full rounded-full bg-[var(--v2-clay)] text-[15px] font-bold text-white shadow-[0_14px_26px_-14px_rgba(var(--v2-rgb-c36c45),0.9)] disabled:opacity-45"
        >
          Saya paham
        </button>
        <button
          onClick={onLater}
          disabled={isBusy}
          className="v2-anim-pressable mt-2 h-[42px] w-full rounded-full border border-[var(--v2-bg-light-7)] bg-[var(--v2-bg-light-8)] text-[13.5px] font-medium text-[var(--v2-ink)] disabled:opacity-50"
        >
          Nanti dulu
        </button>

        <p className="mt-2.5 flex items-center justify-center gap-1.5 text-[11.5px] font-medium text-[var(--v2-muted-tertiary)]">
          <Lock className="h-[12px] w-[12px]" /> Keamanan dan privasi kamu penting bagi kami.
        </p>
      </aside>
    </div>
  );
}

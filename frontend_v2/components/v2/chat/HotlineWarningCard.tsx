'use client';

import Link from 'next/link';
import { ChevronRight, Heart, Lock, PhoneCall, Shield } from '@/lib/assets';

const IMMEDIATE_HELP_TEL = 'tel:119';

// crisis support card shown under a reply flagged crisisTier 1 or 2; "Hubungi orang terdekat" dials the crisis line directly
export function HotlineWarningCard() {
  return (
    <div className="w-full max-w-[92%] rounded-[20px] border border-[var(--v2-line)] bg-[#fbf3ea] p-4">
      <div className="flex items-start gap-3">
        <span className="relative grid h-[46px] w-[46px] shrink-0 place-items-center rounded-full bg-[#f3ded0]">
          <Shield className="h-[24px] w-[24px] text-[#c05b33]" fill="#c05b33" strokeWidth={0} />
          <Heart className="absolute h-[12px] w-[12px] text-white" fill="white" />
        </span>
        <div className="min-w-0">
          <p className="text-[15px] font-bold leading-tight text-[var(--v2-ink)]">Dukungan segera</p>
          <p className="mt-0.5 text-[13.5px] font-bold leading-snug text-[#c05b33]">
            Kalau kamu butuh bantuan sekarang
          </p>
          <p className="mt-1.5 text-[13px] font-medium leading-[1.5] text-[#55524a]">
            Perasaan ini bisa datang kapan saja. Kalau kamu merasa kewalahan atau butuh bicara dengan
            seseorang sekarang, jangan ragu untuk minta bantuan. Kamu berharga dan layak untuk didukung.
          </p>
        </div>
      </div>

      <div className="mt-3.5 border-t border-[var(--v2-line)] pt-3.5">
        <div className="flex items-start gap-2.5">
          <span className="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-full bg-[var(--v2-olive-soft)] text-[var(--v2-olive-deep)]">
            <PhoneCall className="h-[16px] w-[16px]" strokeWidth={2.2} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[13.5px] font-bold leading-tight text-[var(--v2-ink)]">
                Butuh seseorang untuk bicara?
              </p>
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-[#f3ede0] px-2.5 py-1 text-[10.5px] font-bold text-[#6b6a63]">
                <Lock className="h-[10px] w-[10px]" /> Aman &amp; rahasia
              </span>
            </div>
            <p className="mt-0.5 text-[12.5px] font-medium leading-[1.45] text-[#55524a]">
              Kamu bisa menghubungi layanan bantuan atau orang terdekat yang kamu percaya.
            </p>
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <Link
            href="/hotlines"
            className="v2-anim-pressable inline-flex min-h-[42px] flex-1 items-center justify-center gap-1.5 rounded-full border border-[var(--v2-line)] bg-transparent px-4 text-[13px] font-bold text-[var(--v2-ink)]"
          >
            Lihat hotline <ChevronRight className="h-[15px] w-[15px]" />
          </Link>
          <a
            href={IMMEDIATE_HELP_TEL}
            className="v2-anim-pressable inline-flex min-h-[42px] flex-1 items-center justify-center gap-1.5 rounded-full bg-[#c05b33] px-4 text-[13px] font-bold text-white"
          >
            Hubungi orang terdekat <ChevronRight className="h-[15px] w-[15px]" />
          </a>
        </div>
      </div>
    </div>
  );
}

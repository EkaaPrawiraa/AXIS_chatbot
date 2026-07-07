'use client';

import Link from 'next/link';
import { ChevronRight, Heart, Lock, Phone } from '@/lib/assets';
import { chatRoomStyles } from '@/lib/styles/chatRoom';

const IMMEDIATE_HELP_TEL = 'tel:119';

// crisis support card shown under a reply flagged crisisTier 1 or 2; "Hubungi orang terdekat" dials the crisis line directly
export function HotlineWarningCard() {
  return (
    <div className={chatRoomStyles.hotlineCardBase}>
      <div className={chatRoomStyles.hotlineRow}>
        <span className={chatRoomStyles.hotlineIconWrapper}>
          <Heart
            className="h-[20px] w-[20px] text-[#E88DA0]"
            fill="currentColor"
            strokeWidth={0}
          />
        </span>
        <div className="min-w-0">
          <p className={chatRoomStyles.hotlineMainTitle}>Dukungan segera</p>
          <p className={chatRoomStyles.hotlineMainSubtitle}>
            Kalau kamu butuh bantuan sekarang
          </p>
          <p className={chatRoomStyles.hotlineMainDesc}>
            Perasaan ini bisa datang kapan saja. Kalau kamu merasa kewalahan atau butuh bicara dengan
            seseorang sekarang, jangan ragu untuk minta bantuan. Kamu berharga dan layak untuk didukung.
          </p>
        </div>
      </div>

      <div className={chatRoomStyles.hotlineDivider}>
        <div className={chatRoomStyles.hotlineRow}>
          <span className={chatRoomStyles.hotlineIconWrapper}>
            <Phone
              className="h-[18px] w-[18px] text-[#DC143C]"
              fill="currentColor"
              strokeWidth={2.2}
            />
          </span>
          <div className="min-w-0 flex-1">
            <div className={chatRoomStyles.hotlineSubTitleRow}>
              <p className={chatRoomStyles.hotlineSubTitle}>
                Butuh seseorang untuk bicara?
              </p>
              <span className={chatRoomStyles.hotlineSubBadge}>
                <Lock className="h-[10px] w-[10px]" strokeWidth={2.5} /> Aman &amp; rahasia
              </span>
            </div>
            <p className={chatRoomStyles.hotlineSubDesc}>
              Kamu bisa menghubungi layanan bantuan atau orang terdekat yang kamu percaya.
            </p>
          </div>
        </div>

        <div className={chatRoomStyles.hotlineButtonGroup}>
          <Link
            href="/hotlines"
            className={chatRoomStyles.hotlineSecondaryBtn}
          >
            Lihat hotline <ChevronRight className="h-[15px] w-[15px]" strokeWidth={2.5} />
          </Link>
          <a
            href={IMMEDIATE_HELP_TEL}
            className={chatRoomStyles.hotlinePrimaryBtn}
          >
            Hubungi kontak darurat <ChevronRight className="h-[15px] w-[15px]" strokeWidth={2.5} />
          </a>
        </div>
      </div>
    </div>
  );
}

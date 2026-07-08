'use client';

import { Smartphone, X } from '@/lib/assets';
import { useEffect, useState } from 'react';

const DISMISS_KEY = 'axis-desktop-warning-dismissed';
const MOBILE_UA = /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i;

function isMobileUserAgent(): boolean {
  if (typeof navigator === 'undefined') return true;
  return MOBILE_UA.test(navigator.userAgent);
}

// nudges real desktop UAs toward a phone
export function DesktopWarningBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = sessionStorage.getItem(DISMISS_KEY) === '1';
    if (!dismissed && !isMobileUserAgent()) setVisible(true);
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, '1');
    setVisible(false);
  };

  return (
    <div className="fixed inset-x-0 top-0 z-[100] flex items-center gap-3 bg-[var(--v2-ink)] px-4 py-2.5 text-white">
      <Smartphone className="h-[18px] w-[18px] shrink-0" />
      <p className="min-w-0 flex-1 text-[12.5px] font-medium leading-snug">
        AXIS dirancang untuk layar HP. Buka di perangkat mobile untuk pengalaman terbaik.
      </p>
      <button onClick={dismiss} aria-label="Tutup" className="v2-anim-pressable shrink-0 text-white/80">
        <X className="h-[16px] w-[16px]" />
      </button>
    </div>
  );
}

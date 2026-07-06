import Image from 'next/image';
import { AxisWordmark } from '@/components/v2/AxisMark';
import { ILLUSTRATIONS } from '@/lib/assets';

/**
 * Auth page hero: AXIS wordmark + tagline, with the watercolor mug
 * illustration (cropped from the v3 reference) flush to the top-right.
 */
export function AuthHero() {
  return (
    <div className="relative">
      <Image
        src={ILLUSTRATIONS.appIcon}
        alt=""
        width={276}
        height={352}
        priority
        className="pointer-events-none absolute -right-7 -top-6 w-[118px] select-none"
      />

      <div className="relative z-10 pt-6">
        <div className="flex justify-center">
          {/* <AxisWordmark className="-translate-x-4" markSize={40} /> */}
          <AxisWordmark className="!text-[22px] !tracking-[0.2em]" markSize={30} mark="monogram" />
        </div>
        <p className="mt-2.5 -translate-x-4 text-center text-[13px] font-medium leading-[1.55] text-[var(--v2-ink)]">
          Teman refleksi harian untuk cerita,
          <br />
          menata pikiran, dan menemanimu.
        </p>
      </div>
    </div>
  );
}

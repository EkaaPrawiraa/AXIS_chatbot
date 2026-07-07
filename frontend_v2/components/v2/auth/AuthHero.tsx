
import { AxisWordmark } from '@/components/v2/AxisMark';


export function AuthHero() {
  return (
    <div className="relative">
      <div className="relative z-10 pt-6">
        <div className="flex justify-center">
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

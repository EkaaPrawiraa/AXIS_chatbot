'use client';

import { AlertTriangle, Loader2, Lock, Sprout, Trash2 } from '@/lib/assets';
import { animationClasses } from '@/lib/animations';

// reset confirmation sheet; only clears KG memory, chat history stays (matches the real API)
export function ResetMemorySheet({
  onConfirm,
  onClose,
  isBusy = false,
}: {
  onConfirm: () => void;
  onClose: () => void;
  isBusy?: boolean;
}) {
  return (
    <div className={`fixed inset-0 z-[85] bg-black/40 ${animationClasses.sheetBackdropIn}`} onClick={onClose}>
      <aside
        onClick={(event) => event.stopPropagation()}
        className={`absolute inset-x-0 bottom-0 mx-auto w-[min(100%,540px)] rounded-t-[28px] bg-[#f9f2e9] px-5 pb-6 pt-2.5 shadow-2xl ${animationClasses.sheetUp}`}
      >
        <span className="mx-auto block h-[5px] w-14 rounded-full bg-[#cfc8b8]" aria-hidden />

        <div className="mt-5 flex items-center gap-4">
          <span className="grid h-[56px] w-[56px] shrink-0 place-items-center rounded-full bg-[#f6e3d3]">
            <AlertTriangle className="h-[26px] w-[26px] text-[#c05b33]" />
          </span>
          <h2 className="text-[24px] font-bold text-[var(--v2-ink)]">Reset memori AXIS?</h2>
        </div>

        <p className="mt-4 text-[15px] font-medium leading-[1.55] text-[var(--v2-ink)]">
          AXIS akan lupa semua memori, catatan, dan preferensimu. Tindakan ini tidak dapat dibatalkan.
        </p>

        <div className="mt-4 flex items-center gap-3.5 rounded-[16px] bg-[#f6ead9] px-4 py-3">
          <Sprout className="h-[24px] w-[24px] shrink-0 text-[#4f6138]" />
          <p className="text-[13.5px] font-medium leading-snug text-[var(--v2-ink)]">
            Riwayat percakapanmu tetap aman dan tidak akan terhapus.
          </p>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={onClose}
            disabled={isBusy}
            className="v2-anim-pressable h-[52px] flex-1 rounded-full border border-[#e5d6c2] bg-[#fbf6ee] text-[15.5px] font-bold text-[var(--v2-ink)] disabled:opacity-50"
          >
            Batal
          </button>
          <button
            onClick={onConfirm}
            disabled={isBusy}
            className="v2-anim-pressable flex h-[52px] flex-1 items-center justify-center gap-2.5 rounded-full bg-[var(--v2-clay)] text-[15.5px] font-bold text-white shadow-[0_14px_26px_-14px_rgba(195,108,69,0.9)] disabled:opacity-60"
          >
            {isBusy ? <Loader2 className="h-[17px] w-[17px] animate-spin" /> : <Trash2 className="h-[17px] w-[17px]" />}
            Reset memori
          </button>
        </div>

        <p className="mt-4 flex items-center justify-center gap-1.5 text-[13px] font-medium text-[var(--v2-ink)]">
          <Lock className="h-[14px] w-[14px]" /> Kami akan tetap menjaga privasimu.
        </p>
      </aside>
    </div>
  );
}

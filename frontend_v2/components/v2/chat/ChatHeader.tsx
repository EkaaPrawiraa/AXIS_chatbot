'use client';

import { ArrowLeft, Edit3, Mic, MoreVertical, Trash2 } from '@/lib/assets';
import { useState } from 'react';
import { AxisWordmark } from '@/components/v2/AxisMark';
import { animationClasses, motionStyleVars } from '@/lib/animations';

// chat room header: back arrow returns to the session list, AXIS wordmark
export function ChatHeader({
  onBack,
  onVoice,
  onRename,
  onDelete,
}: {
  onBack: () => void;
  onVoice?: () => void;
  onRename?: () => void;
  onDelete?: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header
      className={`sticky top-0 z-20 -mx-[22px] flex items-center gap-2 bg-[rgb(250_244_235_/_0.92)] px-[22px] pb-2.5 pt-1.5 backdrop-blur-lg ${animationClasses.staggerItem}`}
      style={motionStyleVars({ delayMs: 35 })}
    >
      {/* animation + z-20 must stay on this element, a separate wrapper div would get its own stacking context and let chat bubbles cover the dropdown */}
      <button onClick={onBack} aria-label="Kembali" className="v2-anim-pressable grid h-9 w-8 place-items-center text-[var(--v2-ink)]">
        <ArrowLeft className="h-[22px] w-[22px]" strokeWidth={2.2} />
      </button>
      <AxisWordmark className="!text-[22px] !tracking-[0.2em]" markSize={30} mark="monogram" />

      <div className="relative ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={onVoice}
          aria-label="Buka Confession Space"
          className="v2-anim-pressable grid h-9 w-9 place-items-center rounded-full text-[var(--v2-ink)]"
        >
          <Mic className="h-[20px] w-[20px]" strokeWidth={2.25} />
        </button>
        <button
          type="button"
          onClick={() => setMenuOpen((value) => !value)}
          aria-label="Opsi sesi"
          aria-expanded={menuOpen}
          className="v2-anim-pressable grid h-9 w-9 place-items-center rounded-full text-[var(--v2-ink)]"
        >
          <MoreVertical className="h-[21px] w-[21px]" strokeWidth={2.25} />
        </button>
        {menuOpen ? (
          <div className="v2-anim-soft-pop absolute right-0 top-10 z-30 w-[198px] overflow-hidden rounded-[18px] border border-[var(--v2-line)] bg-[#fffaf3] p-1.5 shadow-[0_18px_42px_rgb(83_67_46_/_0.16)]">
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onRename?.();
              }}
              className="flex w-full items-center gap-2.5 rounded-[13px] px-3 py-2.5 text-left text-[13.5px] font-bold text-[var(--v2-ink)]"
            >
              <Edit3 className="h-4 w-4" strokeWidth={2.2} />
              Edit judul sesi
            </button>
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                onDelete?.();
              }}
              className="flex w-full items-center gap-2.5 rounded-[13px] px-3 py-2.5 text-left text-[13.5px] font-bold text-[#a7462e]"
            >
              <Trash2 className="h-4 w-4" strokeWidth={2.2} />
              Hapus sesi
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

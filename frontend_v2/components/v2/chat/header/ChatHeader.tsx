'use client';

import { ArrowLeft, Edit3, Mic, MoreVertical, Trash2 } from '@/lib/assets';
import { useState } from 'react';
import { AxisWordmark } from '@/components/v2/AxisMark';
import { animationClasses, motionStyleVars } from '@/lib/animations';
import { chatRoomStyles } from '@/lib/styles/chatRoom';

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
      className={`${chatRoomStyles.headerWrapper} ${animationClasses.staggerItem}`}
      style={motionStyleVars({ delayMs: 100 })}
    >
      <button onClick={onBack} aria-label="Kembali" className={chatRoomStyles.headerBackBtn}>
        <ArrowLeft className="h-[22px] w-[22px]" strokeWidth={2.2} />
      </button>
      <AxisWordmark className="!text-[22px] !tracking-[0.2em]" markSize={30} mark="monogram" />

      <div className={chatRoomStyles.headerActionsWrapper}>
        {onVoice ? (
          <button onClick={onVoice} aria-label="Percakapan Suara" className={chatRoomStyles.headerIconBtn}>
            <Mic className="h-[20px] w-[20px]" strokeWidth={2.25} />
          </button>
        ) : null}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Menu Opsi"
          className={chatRoomStyles.headerIconBtn}
        >
          <MoreVertical className="h-[18px] w-[18px]" strokeWidth={2.5} />
        </button>

        {menuOpen ? (
          <>
            <div className="fixed inset-0 z-[-1]" onClick={() => setMenuOpen(false)} />
            <div className={`${chatRoomStyles.headerDropdown} ${animationClasses.softPop}`}>
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onRename?.();
                }}
                className={chatRoomStyles.headerDropdownItem}
              >
                <Edit3 className="h-[16px] w-[16px] text-[var(--v2-muted)]" strokeWidth={2.2} />
                Ganti Judul
              </button>
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onDelete?.();
                }}
                className={chatRoomStyles.headerDropdownItemDanger}
              >
                <Trash2 className="h-[16px] w-[16px]" />
                Hapus Sesi
              </button>
            </div>
          </>
        ) : null}
      </div>
    </header>
  );
}

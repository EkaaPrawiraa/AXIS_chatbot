'use client';

import { AlertTriangle, Loader2, Trash2 } from '@/lib/assets';
import { useState } from 'react';
import { animationClasses } from '@/lib/animations';

const CONFIRM_WORD = 'HAPUS';


export function DeleteAccountSheet({
  onConfirm,
  onClose,
  isBusy = false,
  errorMessage,
}: {
  onConfirm: (password: string) => void;
  onClose: () => void;
  isBusy?: boolean;
  errorMessage?: string | null;
}) {
  const [confirmText, setConfirmText] = useState('');
  const [password, setPassword] = useState('');

  const canSubmit = confirmText.trim().toUpperCase() === CONFIRM_WORD && password.length > 0 && !isBusy;

  return (
    <div className={`fixed inset-0 z-[85] bg-black/40 ${animationClasses.sheetBackdropIn}`} onClick={onClose}>
      <aside
        onClick={(event) => event.stopPropagation()}
        className={`absolute inset-x-0 bottom-0 mx-auto w-[min(100%,540px)] rounded-t-[28px] bg-[var(--v2-c-f9f2e9)] px-5 pb-6 pt-2.5 shadow-2xl ${animationClasses.sheetUp}`}
      >
        <span className="mx-auto block h-[5px] w-14 rounded-full bg-[var(--v2-line-border)]" aria-hidden />

        <div className="mt-5 flex items-center gap-4">
          <span className="grid h-[56px] w-[56px] shrink-0 place-items-center rounded-full bg-[var(--v2-bg-light-5)]">
            <AlertTriangle className="h-[26px] w-[26px] text-[var(--v2-clay-accent)]" />
          </span>
          <h2 className="text-[22px] font-bold leading-tight text-[var(--v2-ink)]">Hapus akun AXIS?</h2>
        </div>

        <p className="mt-4 text-[14.5px] font-medium leading-[1.55] text-[var(--v2-ink)]">
          Semua percakapan, memori, dan data profil kamu akan dihapus secara permanen. Tindakan ini{' '}
          <span className="font-bold">tidak dapat dibatalkan</span>.
        </p>

        <div className="mt-4 space-y-3">
          <div>
            <label className="text-[12.5px] font-bold text-[var(--v2-green-tertiary)]">
              Ketik <span className="text-[var(--v2-clay-accent)]">{CONFIRM_WORD}</span> untuk konfirmasi
            </label>
            <input
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              placeholder={CONFIRM_WORD}
              className="mt-1 w-full rounded-[12px] border border-[var(--v2-bg-light-7)] bg-white/70 px-3.5 py-2.5 text-[14.5px] font-bold text-[var(--v2-ink)] outline-none"
            />
          </div>
          <div>
            <label className="text-[12.5px] font-bold text-[var(--v2-green-tertiary)]">Masukkan password kamu</label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              className="mt-1 w-full rounded-[12px] border border-[var(--v2-bg-light-7)] bg-white/70 px-3.5 py-2.5 text-[14.5px] font-semibold text-[var(--v2-ink)] outline-none"
            />
          </div>
        </div>

        {errorMessage ? (
          <p className="mt-3 rounded-[12px] bg-[var(--v2-bg-light-5)] px-3.5 py-2 text-[13px] font-semibold text-[var(--v2-c-a34a28)]">
            {errorMessage}
          </p>
        ) : null}

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={onClose}
            disabled={isBusy}
            className="v2-anim-pressable h-[52px] flex-1 rounded-full border border-[var(--v2-bg-light-7)] bg-[var(--v2-bg-light-8)] text-[15.5px] font-bold text-[var(--v2-ink)] disabled:opacity-50"
          >
            Batal
          </button>
          <button
            onClick={() => onConfirm(password)}
            disabled={!canSubmit}
            className="v2-anim-pressable flex h-[52px] flex-1 items-center justify-center gap-2.5 rounded-full bg-[var(--v2-clay)] text-[15.5px] font-bold text-white shadow-[0_14px_26px_-14px_rgba(var(--v2-rgb-c36c45),0.9)] disabled:opacity-40"
          >
            {isBusy ? <Loader2 className="h-[17px] w-[17px] animate-spin" /> : <Trash2 className="h-[17px] w-[17px]" />}
            Hapus akun
          </button>
        </div>
      </aside>
    </div>
  );
}

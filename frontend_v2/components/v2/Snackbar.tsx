'use client';

import { AlertCircle, CheckCircle2, Info, X } from '@/lib/assets';
import { useEffect } from 'react';
import { animationClasses } from '@/lib/animations';
import { useUIStore } from '@/stores/ui';

const AUTO_DISMISS_MS = 4200;

const TYPE_STYLE = {
  success: { bg: 'var(--v2-c-eef0e2)', text: 'var(--v2-green-secondary)', Icon: CheckCircle2 },
  error: { bg: 'var(--v2-bg-light-5)', text: 'var(--v2-c-a34a28)', Icon: AlertCircle },
  info: { bg: 'var(--v2-c-eae6da)', text: 'var(--v2-c-5a5648)', Icon: Info },
} as const;


export function Snackbar() {
  const toasts = useUIStore((state) => state.toasts);
  const removeToast = useUIStore((state) => state.removeToast);

  return (
    <div className="pointer-events-none fixed right-3 top-3 z-[200] flex w-[min(88vw,360px)] flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} id={toast.id} type={toast.type} message={toast.message} onDismiss={removeToast} />
      ))}
    </div>
  );
}

function ToastItem({
  id,
  type,
  message,
  onDismiss,
}: {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
  onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(id), AUTO_DISMISS_MS);
    return () => window.clearTimeout(timer);
  }, [id, onDismiss]);

  const style = TYPE_STYLE[type];

  return (
    <div
      className={`pointer-events-auto flex items-start gap-2.5 rounded-[14px] px-3.5 py-3 shadow-[0_14px_28px_-16px_rgba(var(--v2-rgb-464035),0.5)] ${animationClasses.softPop}`}
      style={{ backgroundColor: style.bg }}
    >
      <style.Icon className="mt-0.5 h-[17px] w-[17px] shrink-0" style={{ color: style.text }} />
      <p className="min-w-0 flex-1 text-[13px] font-semibold leading-snug" style={{ color: style.text }}>
        {message}
      </p>
      <button onClick={() => onDismiss(id)} aria-label="Tutup" className="v2-anim-pressable shrink-0" style={{ color: style.text }}>
        <X className="h-[14px] w-[14px]" />
      </button>
    </div>
  );
}

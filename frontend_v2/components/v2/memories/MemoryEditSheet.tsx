'use client';

import Image from 'next/image';
import { ILLUSTRATIONS, ShieldCheck, Trash2, X } from '@/lib/assets';
import { useMemo, useState } from 'react';
import { animationClasses } from '@/lib/animations';
import type { MemoryNode } from '@/models';

const TITLE_FIELDS = ['name', 'title'];
const CONTENT_FIELDS = ['summary', 'description', 'content'];
const CONTENT_MAX = 500;
const SENSITIVE_LEVELS = new Set(['sensitive', 'trauma']);

function asText(value: unknown): string {
  if (Array.isArray(value)) return value.join(', ');
  return value === null || value === undefined ? '' : String(value);
}

/**
 * "Edit memori" bottom sheet per the v3 design (07_memory_edit_keyboard):
 * book illustration + judul field, isi textarea with 500-char counter,
 * Sensitif toggle (sensitivity_level), and Hapus / Batal / Simpan actions.
 * Any remaining editable fields render as compact inputs so the full v1
 * editing contract is preserved.
 */
export function MemoryEditSheet({
  node,
  onSave,
  onDelete,
  onClose,
  isBusy = false,
}: {
  node: MemoryNode;
  onSave: (properties: Record<string, unknown>) => void;
  onDelete: () => void;
  onClose: () => void;
  isBusy?: boolean;
}) {
  const titleField = useMemo(
    () => TITLE_FIELDS.find((field) => node.editableFields.includes(field)) || null,
    [node]
  );
  const contentField = useMemo(
    () => CONTENT_FIELDS.find((field) => node.editableFields.includes(field)) || null,
    [node]
  );
  const hasSensitivity = node.editableFields.includes('sensitivity_level');
  const extraFields = node.editableFields.filter(
    (field) => field !== titleField && field !== contentField && field !== 'sensitivity_level'
  );

  const [form, setForm] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    node.editableFields.forEach((field) => {
      initial[field] = asText(node.properties[field]);
    });
    return initial;
  });
  const sensitive = SENSITIVE_LEVELS.has((form.sensitivity_level || '').toLowerCase());

  const setField = (field: string, value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  const submit = () => {
    const properties: Record<string, unknown> = {};
    node.editableFields.forEach((field) => {
      properties[field] = form[field] ?? '';
    });
    onSave(properties);
  };

  const contentValue = contentField ? form[contentField] || '' : '';

  return (
    <div className={`fixed inset-0 z-[80] bg-black/35 ${animationClasses.sheetBackdropIn}`} onClick={onClose}>
      <aside
        onClick={(event) => event.stopPropagation()}
        className={`absolute inset-x-0 bottom-0 mx-auto max-h-[88dvh] w-[min(100%,540px)] overflow-y-auto rounded-t-[26px] bg-[#f7f1e8] px-4 pb-5 pt-2 shadow-2xl ${animationClasses.sheetUp}`}
      >
        <span className="mx-auto block h-[5px] w-12 rounded-full bg-[#cfc8b8]" aria-hidden />

        <div className="mt-3 flex items-center justify-between">
          <h2 className="text-[24px] font-bold text-[var(--v2-ink)]">Edit memori</h2>
          <button onClick={onClose} aria-label="Tutup" className="v2-anim-pressable p-1 text-[var(--v2-ink)]">
            <X className="h-[22px] w-[22px]" />
          </button>
        </div>

        <div className="mt-4 flex gap-3">
          <span className="grid h-[88px] w-[104px] shrink-0 place-items-center rounded-[16px] border border-[#e7dfcd] bg-[#fbf7ee]">
            <Image src={ILLUSTRATIONS.memoryBook} alt="" width={140} height={155} className="h-[64px] w-auto" />
          </span>
          {titleField ? (
            <label className="min-w-0 flex-1 rounded-[16px] border border-[#e3dbc8] bg-[#fbf7ee] px-3.5 py-2.5">
              <span className="block text-[12px] font-medium text-[var(--v2-muted)]">Judul memori</span>
              <input
                value={form[titleField] || ''}
                onChange={(event) => setField(titleField, event.target.value)}
                className="mt-1 w-full bg-transparent text-[15px] font-semibold text-[var(--v2-ink)] outline-none"
              />
            </label>
          ) : (
            <div className="min-w-0 flex-1 rounded-[16px] border border-[#e3dbc8] bg-[#fbf7ee] px-3.5 py-2.5">
              <span className="block text-[12px] font-medium text-[var(--v2-muted)]">Judul memori</span>
              <p className="mt-1 truncate text-[15px] font-semibold text-[var(--v2-ink)]">
                {node.title || node.label}
              </p>
            </div>
          )}
        </div>

        {contentField ? (
          <label className="mt-3 block rounded-[16px] border border-[#e3dbc8] bg-[#fbf7ee] px-3.5 py-2.5">
            <span className="block text-[12px] font-medium text-[var(--v2-muted)]">Isi memori</span>
            <textarea
              value={contentValue}
              maxLength={CONTENT_MAX}
              onChange={(event) => setField(contentField, event.target.value)}
              rows={5}
              className="mt-1 w-full resize-none bg-transparent text-[14.5px] font-medium leading-[1.55] text-[var(--v2-ink)] outline-none"
            />
            <span className="block text-right text-[12px] font-medium text-[var(--v2-muted)]">
              {contentValue.length}/{CONTENT_MAX}
            </span>
          </label>
        ) : null}

        {extraFields.length ? (
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            {extraFields.map((field) => {
              const options = node.enumFields?.[field];
              return (
                <label key={field} className="rounded-[14px] border border-[#e3dbc8] bg-[#fbf7ee] px-3 py-2">
                  <span className="block text-[11px] font-medium capitalize text-[var(--v2-muted)]">
                    {field.replace(/_/g, ' ')}
                  </span>
                  {options?.length ? (
                    <select
                      value={form[field] || ''}
                      onChange={(event) => setField(field, event.target.value)}
                      className="mt-0.5 w-full bg-transparent text-[13px] font-semibold text-[var(--v2-ink)] outline-none"
                    >
                      {options.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={form[field] || ''}
                      onChange={(event) => setField(field, event.target.value)}
                      className="mt-0.5 w-full bg-transparent text-[13px] font-semibold text-[var(--v2-ink)] outline-none"
                    />
                  )}
                </label>
              );
            })}
          </div>
        ) : null}

        {hasSensitivity ? (
          <div className="mt-3 flex items-center justify-between rounded-[16px] border border-[#e7dfcd] bg-[#fbf7ee] px-3.5 py-2.5">
            <div className="flex items-center gap-3">
              <span className="grid h-[38px] w-[38px] place-items-center rounded-full bg-[#71805c] text-white">
                <ShieldCheck className="h-[18px] w-[18px]" />
              </span>
              <span className="text-[14.5px] font-semibold text-[var(--v2-ink)]">Sensitif</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={sensitive}
              onClick={() => setField('sensitivity_level', sensitive ? 'normal' : 'sensitive')}
              className={`relative h-[28px] w-[50px] rounded-full transition-colors ${
                sensitive ? 'bg-[var(--v2-olive)]' : 'bg-[#ddd5c4]'
              }`}
            >
              <span
                className={`absolute top-[3px] h-[22px] w-[22px] rounded-full bg-white shadow transition-all ${
                  sensitive ? 'left-[25px]' : 'left-[3px]'
                }`}
              />
            </button>
          </div>
        ) : null}

        <div className="mt-4 flex items-center gap-2.5">
          <button
            onClick={onDelete}
            disabled={isBusy}
            className="v2-anim-pressable flex h-[46px] flex-1 items-center justify-center gap-2 rounded-full border border-[#e3dbc8] bg-[#fbf7ee] text-[14.5px] font-bold text-[var(--v2-clay)] disabled:opacity-50"
          >
            <Trash2 className="h-[16px] w-[16px]" /> Hapus
          </button>
          <button
            onClick={onClose}
            disabled={isBusy}
            className="v2-anim-pressable h-[46px] flex-1 rounded-full border border-[#e3dbc8] bg-[#fbf7ee] text-[14.5px] font-bold text-[var(--v2-ink)] disabled:opacity-50"
          >
            Batal
          </button>
          <button
            onClick={submit}
            disabled={isBusy}
            className="v2-anim-pressable h-[46px] flex-1 rounded-full bg-[var(--v2-clay)] text-[14.5px] font-bold text-white shadow-[0_12px_22px_-12px_rgba(195,108,69,0.9)] disabled:opacity-50"
          >
            Simpan
          </button>
        </div>
      </aside>
    </div>
  );
}

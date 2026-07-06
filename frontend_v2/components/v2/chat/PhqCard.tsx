'use client';

import Image from 'next/image';
import { Frown, ILLUSTRATIONS, Info, Meh, Smile } from '@/lib/assets';
import { AxisMark } from '@/components/v2/AxisMark';
import { animationClasses } from '@/lib/animations';

const FACE_STYLES = [
  { Icon: Smile, color: '#5f9e54' },
  { Icon: Meh, color: '#d9a514' },
  { Icon: Frown, color: '#e07b39' },
  { Icon: Frown, color: '#d84f45' },
] as const;

/**
 * PHQ-9 mood-check card per the v3 design (04_chat_mood_check_phq):
 * illustrated header, "N dari 9" progress bar, bold question, four
 * emoji-face option pills, and an "Apa ini?" clarification link.
 */
export function PhqCard({
  question,
  current,
  total,
  options,
  disabled = false,
  onAnswer,
  onAskWhat,
}: {
  question: string;
  current: number;
  total: number;
  options: Array<{ score: number | null; label: string }>;
  disabled?: boolean;
  onAnswer: (label: string) => void;
  onAskWhat?: () => void;
}) {
  return (
    <div className={`w-full overflow-hidden rounded-[16px] border border-[#ece5d6] bg-[#f7f2eb] shadow-[0_10px_24px_-18px_rgba(70,64,53,0.45)] ${animationClasses.chatBubbleIn}`}>
      <div className="relative h-[90px] bg-[#f4efe3]">
        <Image
          src={ILLUSTRATIONS.phqHeader}
          alt=""
          width={205}
          height={220}
          priority
          className="absolute right-0 top-0 h-full w-auto [mask-image:linear-gradient(to_right,transparent,black_26px)]"
        />
        <div className="relative flex h-full items-center gap-2.5 pl-3.5 pr-[76px]">
          <span className="flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-full bg-[#fbf7ee]">
            <AxisMark className="h-[17px] w-[17px]" />
          </span>
          <div>
            <p className="whitespace-nowrap text-[17px] font-bold leading-tight text-[var(--v2-ink)]">
              Cek suasana hatimu ✨
            </p>
            <p className="mt-0.5 text-[11.5px] font-medium leading-snug text-[var(--v2-muted)]">
              Bantu kamu memahami dirimu hari ini, langkah demi langkah.
            </p>
          </div>
        </div>
      </div>

      <div className="px-3.5 pb-3.5 pt-3">
        <p className="text-[13px] font-bold text-[#5c6549]">
          {current} dari {total}
        </p>
        <div className="mt-1.5 h-[5px] overflow-hidden rounded-full bg-[#dbd5c4]">
          <div
            className={`h-full rounded-full bg-[#717b5e] transition-[width] ${animationClasses.progressGrow}`}
            style={{ width: `${Math.min(100, (current / Math.max(total, 1)) * 100)}%` }}
          />
        </div>

        <p className="mt-3 text-[15px] font-bold leading-[1.45] text-[var(--v2-ink)]">{question}</p>

        <div className="mt-3 space-y-[6px]">
          {options.map((option, index) => {
            const face = FACE_STYLES[Math.min(index, FACE_STYLES.length - 1)];
            return (
              <button
                key={option.label}
                type="button"
                disabled={disabled}
                onClick={() => onAnswer(option.label)}
                className="v2-anim-pressable flex h-[26px] w-full items-center gap-2 rounded-full border border-[#e3dcc9] bg-[#fdfaf3] px-1.5 text-left disabled:opacity-45"
              >
                <face.Icon className="h-[16px] w-[16px] shrink-0" style={{ color: face.color }} strokeWidth={2.2} />
                <span className="text-[12px] font-semibold text-[var(--v2-ink)]">{option.label}</span>
              </button>
            );
          })}
        </div>

        {onAskWhat ? (
          <button
            type="button"
            disabled={disabled}
            onClick={onAskWhat}
            className="v2-anim-pressable mt-3 flex items-center gap-1.5 text-[12px] font-semibold text-[#717b5e] disabled:opacity-45"
          >
            <Info className="h-[13px] w-[13px]" />
            <span className="underline underline-offset-2">Apa ini?</span>
          </button>
        ) : null}
      </div>
    </div>
  );
}

/**
 * Split a PHQ item message into the conversational intro (rendered as a
 * normal bubble) and the question shown inside the card. The agentic
 * service emits: "<ack>\n\nPertanyaan N dari 9. <header>:\n\n<item>\n\n  0. ...".
 */
export function parsePhqContent(content: string): { intro: string; question: string | null } {
  const header = content.match(/(?:Pertanyaan|Question)\s+\d+\s+(?:dari|of)\s+\d+\.?\s*/i);
  if (!header || header.index === undefined) {
    return { intro: content.trim(), question: null };
  }
  const intro = content.slice(0, header.index).trim();
  const rest = content.slice(header.index + header[0].length);
  const question = rest
    .split(/\n\s*0\./)[0]
    .replace(/\s*\n+\s*/g, ' ')
    .trim();
  return { intro, question: question || null };
}

'use client';

import { Frown, Info, Meh, Smile } from '@/lib/assets';
import { animationClasses } from '@/lib/animations';
import { chatRoomStyles } from '@/lib/styles/chatRoom';

const FACE_STYLES = [
  { Icon: Smile, color: '#84cc16' }, // Match dashboard Lime
  { Icon: Meh, color: '#eab308' },   // Match dashboard Yellow
  { Icon: Frown, color: '#f97316' }, // Match dashboard Orange
  { Icon: Frown, color: '#ef4444' }, // Match dashboard Red
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
    <div className={`${chatRoomStyles.phqCardBase} ${animationClasses.chatBubbleIn}`}>
      <div className={chatRoomStyles.phqHeader}>
        <p className={chatRoomStyles.phqHeaderTitle}>
          Cek suasana hatimu
        </p>
        <p className={chatRoomStyles.phqHeaderSubtitle}>
          Bantu kamu memahami dirimu hari ini, langkah demi langkah.
        </p>
      </div>

      <div className={chatRoomStyles.phqBody}>
        <p className={chatRoomStyles.phqStepText}>
          {current} dari {total}
        </p>
        <div className={chatRoomStyles.phqProgressContainer}>
          <div
            className={`${chatRoomStyles.phqProgressBar} ${animationClasses.progressGrow}`}
            style={{ width: `${Math.min(100, (current / Math.max(total, 1)) * 100)}%` }}
          />
        </div>

        <p className={chatRoomStyles.phqQuestion}>{question}</p>

        <div className={chatRoomStyles.phqOptionsContainer}>
          {options.map((option, index) => {
            const face = FACE_STYLES[Math.min(index, FACE_STYLES.length - 1)];
            return (
              <button
                key={option.label}
                type="button"
                disabled={disabled}
                onClick={() => onAnswer(option.label)}
                className={chatRoomStyles.phqOptionBtn}
              >
                <face.Icon className="h-[18px] w-[18px] shrink-0" style={{ color: face.color }} strokeWidth={2.2} />
                <span className={chatRoomStyles.phqOptionText}>{option.label}</span>
              </button>
            );
          })}
        </div>

        {onAskWhat ? (
          <button
            type="button"
            disabled={disabled}
            onClick={onAskWhat}
            className={chatRoomStyles.phqInfoBtn}
          >
            <Info className="h-[14px] w-[14px]" />
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

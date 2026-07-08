import type { CSSProperties } from 'react';



export const animationTimings = {
  quick: 140,
  standard: 240,
  calm: 360,
  slow: 520,
} as const;

export const animationEasings = {
  standard: 'cubic-bezier(0.22, 1, 0.36, 1)',
  gentle: 'cubic-bezier(0.16, 1, 0.3, 1)',
  press: 'cubic-bezier(0.2, 0, 0, 1)',
} as const;

export const animationClasses = {
  pageEnter: 'v2-anim-page-enter',
  cardEnter: 'v2-anim-card-enter',
  fieldGroupEnter: 'v2-anim-field-group-enter',
  softPop: 'v2-anim-soft-pop',
  pressable: 'v2-anim-pressable',
  segmentIndicator: 'v2-anim-segment-indicator',
  heroEnter: 'v2-anim-hero-enter',
  staggerItem: 'v2-anim-stagger-item',
  imageFloat: 'v2-anim-image-float',
  chatBubbleIn: 'v2-anim-chat-bubble-in',
  typingDot: 'v2-anim-typing-dot',
  composerIn: 'v2-anim-composer-in',
  sheetBackdropIn: 'v2-anim-sheet-backdrop-in',
  sheetUp: 'v2-anim-sheet-up',
  progressGrow: 'v2-anim-progress-grow',
} as const;

export function motionStyleVars(vars?: {
  durationMs?: number;
  delayMs?: number;
  easing?: string;
}): CSSProperties {
  return {
    '--v2-motion-duration': `${vars?.durationMs ?? animationTimings.standard}ms`,
    '--v2-motion-delay': `${vars?.delayMs ?? 0}ms`,
    '--v2-motion-ease': vars?.easing ?? animationEasings.standard,
  } as CSSProperties;
}

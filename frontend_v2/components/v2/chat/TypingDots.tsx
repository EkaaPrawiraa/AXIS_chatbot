import { animationClasses } from '@/lib/animations';

/**
 * WhatsApp-style three-dot "typing" indicator, shown in the assistant
 * bubble's place while a streamed reply has been requested but no token
 * has arrived yet (server-side guardrails/memory retrieval/LLM
 * first-token latency) — see AssistantBubble's isStreaming prop.
 */
export function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-0.5" aria-label="AXIS sedang mengetik" role="status">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className={`h-[6px] w-[6px] rounded-full bg-[var(--v2-muted)] ${animationClasses.typingDot}`}
          style={{ animationDelay: `${index * 160}ms` }}
        />
      ))}
    </div>
  );
}

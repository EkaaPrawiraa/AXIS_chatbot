import { animationClasses, motionStyleVars } from '@/lib/animations';
import { chatRoomStyles } from '@/lib/styles/chatRoom';

/**
 * WhatsApp-style three-dot "typing" indicator, shown in the assistant
 * bubble's place while a streamed reply has been requested but no token
 * has arrived yet (server-side guardrails/memory retrieval/LLM
 * first-token latency) — see AssistantBubble's isStreaming prop.
 */
export function TypingDots() {
  return (
    <div className={chatRoomStyles.typingContainer} aria-label="AXIS sedang mengetik" role="status">
      {[0, 150, 300].map((delay, i) => (
        <span
          key={i}
          className={`${chatRoomStyles.typingDot} ${animationClasses.typingDot}`}
          style={motionStyleVars({ delayMs: delay })}
        />
      ))}
    </div>
  );
}

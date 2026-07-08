import { animationClasses, motionStyleVars } from '@/lib/animations';
import { chatRoomStyles } from '@/lib/styles/chatRoom';


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

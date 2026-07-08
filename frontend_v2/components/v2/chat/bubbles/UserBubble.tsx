import { CheckCheck } from '@/lib/assets';
import type { Message } from '@/models';
import { formatChatTime } from '@/components/v2/chat/utils/format';
import { animationClasses } from '@/lib/animations';
import { chatRoomStyles } from '@/lib/styles/chatRoom';


export function UserBubble({ message }: { message: Message }) {
  return (
    <div data-bubble="user" className={`${chatRoomStyles.userBubbleWrapper} ${animationClasses.chatBubbleIn}`}>
      <span className={chatRoomStyles.userBubbleText}>{message.content}</span>
      <span className={chatRoomStyles.userTimestamp}>
        {formatChatTime(message.createdAt)} <CheckCheck className="h-[13px] w-[13px]" />
      </span>
    </div>
  );
}

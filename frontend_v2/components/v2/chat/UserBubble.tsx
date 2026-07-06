import { CheckCheck } from '@/lib/assets';
import type { Message } from '@/models';
import { formatChatTime } from '@/components/v2/chat/format';
import { animationClasses } from '@/lib/animations';

/**
 * User chat bubble: soft olive fill, white text, inline timestamp with
 * double-check mark bottom-right — per the v3 chat design.
 */
export function UserBubble({ message }: { message: Message }) {
  return (
    <div data-bubble="user" className={`ml-auto w-fit max-w-[80%] rounded-[12px] bg-[#7b8467] px-3.5 py-2 text-[14px] font-medium leading-[1.5] text-white ${animationClasses.chatBubbleIn}`}>
      <span className="whitespace-pre-wrap">{message.content}</span>
      <span className="mt-0.5 flex items-center justify-end gap-1 text-[10.5px] font-medium text-white/85">
        {formatChatTime(message.createdAt)} <CheckCheck className="h-[13px] w-[13px]" />
      </span>
    </div>
  );
}

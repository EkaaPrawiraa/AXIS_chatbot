import { useQuery } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { Message, ID } from '@/models';

export function useChatMessages(
  conversationId: ID | null,
  page: number = 1,
  pageSize: number = 100,
  enabled: boolean = true
) {
  return useQuery<Message[]>({
    queryKey: ['messages', conversationId, page, pageSize],
    queryFn: async () => {
      if (!conversationId) throw new Error('Conversation ID is required');
      const messages: Message[] = [];
      let currentPage = page;

      while (true) {
        const batch = await chatAPI.getMessages(conversationId, currentPage, pageSize);
        messages.push(...batch);
        if (batch.length < pageSize) break;
        currentPage += 1;
      }

      return messages;
    },
    enabled: !!conversationId && enabled,
  });
}

import { useQuery } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { useSessionStore } from '@/stores';
import { Message, ID } from '@/models';

export function useChatMessages(
  conversationId: ID | null,
  page: number = 1,
  pageSize: number = 100,
  enabled: boolean = true
) {
  const userId = useSessionStore((state) => state.userId);

  return useQuery<Message[]>({
    queryKey: ['messages', conversationId, page, pageSize],
    queryFn: async () => {
      if (!conversationId) throw new Error('Conversation ID is required');
      const messages: Message[] = [];
      let currentPage = page;

      while (true) {
        const batch = await chatAPI.getMessages(conversationId, currentPage, pageSize, userId ?? undefined);
        messages.push(...batch);
        if (batch.length < pageSize) break;
        currentPage += 1;
      }

      return messages;
    },
    enabled: !!conversationId && enabled,
    // Poll every 3 s when the DB contains an in-progress streaming message so
    // the client picks up the final status after a page refresh mid-stream.
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!Array.isArray(data)) return false;
      return data.some((m: Message) => m.status === 'sending') ? 3_000 : false;
    },
  });
}

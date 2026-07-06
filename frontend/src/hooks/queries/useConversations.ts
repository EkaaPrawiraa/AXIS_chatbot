import { useQuery } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { Conversation, ID } from '@/models';

export function useConversations(userId: ID | null, enabled: boolean = true) {
  return useQuery<Conversation[]>({
    queryKey: ['conversations', userId],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return chatAPI.getConversations(userId);
    },
    enabled: !!userId && enabled,
  });
}

export function useConversation(conversationId: ID | null, enabled: boolean = true) {
  return useQuery<Conversation>({
    queryKey: ['conversations', conversationId],
    queryFn: async () => {
      if (!conversationId) throw new Error('Conversation ID is required');
      const conversations = await chatAPI.getConversations('current-user');
      return conversations.find((c) => c.id === conversationId) || ({} as Conversation);
    },
    enabled: !!conversationId && enabled,
  });
}

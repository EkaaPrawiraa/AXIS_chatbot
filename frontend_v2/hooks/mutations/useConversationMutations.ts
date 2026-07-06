import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { ID } from '@/models';

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, title }: { userId: ID; title: string }) =>
      chatAPI.createConversation(userId, title),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', conversation.userId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: ID) => chatAPI.deleteConversation(conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '@/lib/api/chat';
import { SendMessageRequest } from '@/models';

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: SendMessageRequest) => chatAPI.sendMessage(request),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['messages', variables.conversationId],
      });

      queryClient.invalidateQueries({
        queryKey: ['conversations'],
      });
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
    },
  });
}

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { moodAPI } from '@/lib/api/mood';

export function useSubmitMood() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (score: number) => moodAPI.submitMood(score),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mood-trend'] });
    },
  });
}

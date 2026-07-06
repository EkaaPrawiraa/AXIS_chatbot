import { useMutation, useQueryClient } from '@tanstack/react-query';
import { reflectionAPI } from '@/lib/api/reflection';
import { Reflection, ID } from '@/models';

export function useSubmitReflection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, reflection }: { userId: ID; reflection: Partial<Reflection> }) =>
      reflectionAPI.submitReflection(userId, reflection),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reflections'] });
    },
  });
}

export function useUpdateReflection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reflectionId, reflection }: { reflectionId: ID; reflection: Partial<Reflection> }) =>
      reflectionAPI.updateReflection(reflectionId, reflection),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['reflections'] });
      queryClient.invalidateQueries({ queryKey: ['reflection', data.id] });
    },
  });
}

export function useDeleteReflection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (reflectionId: ID) => reflectionAPI.deleteReflection(reflectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reflections'] });
    },
  });
}

export function useAnalyzeCBT() {
  return useMutation({
    mutationFn: (cbtSession: any) => reflectionAPI.analyzeCBT(cbtSession),
  });
}

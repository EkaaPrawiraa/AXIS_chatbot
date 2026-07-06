import { useQuery } from '@tanstack/react-query';
import { reflectionAPI } from '@/lib/api/reflection';
import { Reflection, ID } from '@/models';

export function useReflections(userId: ID | null, enabled: boolean = true) {
  return useQuery<Reflection[]>({
    queryKey: ['reflections', userId],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return reflectionAPI.getReflections(userId);
    },
    enabled: !!userId && enabled,
  });
}

export function useReflection(reflectionId: ID | null, enabled: boolean = true) {
  return useQuery<Reflection>({
    queryKey: ['reflection', reflectionId],
    queryFn: () => {
      if (!reflectionId) throw new Error('Reflection ID is required');
      return reflectionAPI.getReflection(reflectionId);
    },
    enabled: !!reflectionId && enabled,
  });
}

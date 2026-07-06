import { useMutation, useQueryClient } from '@tanstack/react-query';
import { profileAPI } from '@/lib/api/profile';
import { UpdateProfileRequest, ID } from '@/models';

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, request }: { userId: ID; request: UpdateProfileRequest }) =>
      profileAPI.updateProfile(userId, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['profile', data.userId] });
    },
  });
}

export function useGeneratePersonalityInsights() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: ID) => profileAPI.generatePersonalityInsights(userId),
    onSuccess: (data, userId) => {
      queryClient.invalidateQueries({ queryKey: ['profile', userId, 'insights'] });
    },
  });
}

import { useQuery } from '@tanstack/react-query';
import { profileAPI } from '@/lib/api/profile';
import { UserProfile, ID } from '@/models';

export function useProfile(userId: ID | null, enabled: boolean = true) {
  return useQuery<UserProfile>({
    queryKey: ['profile', userId],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return profileAPI.getProfile(userId);
    },
    enabled: !!userId && enabled,
  });
}

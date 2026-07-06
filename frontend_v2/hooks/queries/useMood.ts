import { useQuery } from '@tanstack/react-query';
import { moodAPI } from '@/lib/api/mood';
import { MoodEntry, ID } from '@/models';

export function useMoodTrend(userId: ID | null, days: number = 14, enabled: boolean = true) {
  return useQuery<MoodEntry[]>({
    queryKey: ['mood-trend', userId, days],
    queryFn: () => moodAPI.getTrend(days),
    enabled: !!userId && enabled,
  });
}

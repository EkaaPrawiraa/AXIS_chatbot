import { useQuery } from '@tanstack/react-query';
import { insightAPI } from '@/lib/api/insight';
import { Insight, InsightSnapshot, ID } from '@/models';

export function useInsights(userId: ID | null, enabled: boolean = true) {
  return useQuery<Insight[]>({
    queryKey: ['insights', userId],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return insightAPI.getInsights(userId);
    },
    enabled: !!userId && enabled,
  });
}

export function useInsightSnapshots(userId: ID | null, enabled: boolean = true) {
  return useQuery<InsightSnapshot[]>({
    queryKey: ['insights', userId, 'snapshots'],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return insightAPI.getSnapshots(userId);
    },
    enabled: !!userId && enabled,
  });
}

export function useInsight(insightId: ID | null, enabled: boolean = true) {
  return useQuery<Insight>({
    queryKey: ['insight', insightId],
    queryFn: () => {
      if (!insightId) throw new Error('Insight ID is required');
      return insightAPI.getInsight(insightId);
    },
    enabled: !!insightId && enabled,
  });
}

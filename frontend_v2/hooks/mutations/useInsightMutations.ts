import { useMutation, useQueryClient } from '@tanstack/react-query';
import { insightAPI } from '@/lib/api/insight';
import { GenerateInsightRequest, InsightExportRequest, ID } from '@/models';

export function useGenerateInsights() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, request }: { userId: ID; request: GenerateInsightRequest }) =>
      insightAPI.generateInsights(userId, request),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['insights', variables.userId] });
    },
  });
}

export function useExportInsights() {
  return useMutation({
    mutationFn: ({ userId, request }: { userId: ID; request: InsightExportRequest }) =>
      insightAPI.exportInsights(userId, request),
  });
}

import { apiClient } from './client';
import { Insight, InsightSnapshot, GenerateInsightRequest, InsightExportRequest, ID } from '@/models';
import { API_ROUTES } from '../constants';

export const insightAPI = {
  getInsights: async (userId: ID) => {
    const response = await apiClient.get<Insight[]>(API_ROUTES.INSIGHTS, {
      params: { userId },
    });
    return response.data.data || [];
  },

  generateInsights: async (userId: ID, request: GenerateInsightRequest) => {
    const response = await apiClient.post<Insight[]>(
      API_ROUTES.INSIGHTS_GENERATE,
      { userId, ...request }
    );
    return response.data.data || [];
  },

  getSnapshots: async (userId: ID) => {
    const response = await apiClient.get<InsightSnapshot[]>(
      '/insights/snapshots',
      { params: { userId } }
    );
    return response.data.data || [];
  },

  exportInsights: async (userId: ID, request: InsightExportRequest) => {
    const response = await apiClient.post(
      '/insights/export',
      { userId, ...request },
      { responseType: 'blob' }
    );
    return response.data;
  },

  getInsight: async (insightId: ID) => {
    const response = await apiClient.get<Insight>(`/insights/${insightId}`);
    return response.data.data!;
  },
};

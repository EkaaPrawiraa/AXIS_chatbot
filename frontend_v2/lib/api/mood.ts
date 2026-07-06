import { apiClient } from './client';
import { MoodEntry } from '@/models';

export const moodAPI = {
  submitMood: async (score: number) => {
    const response = await apiClient.post<MoodEntry>('/mood', { score });
    return response.data.data!;
  },

  getTrend: async (days: number = 14) => {
    const response = await apiClient.get<MoodEntry[]>('/mood/trend', { params: { days } });
    return response.data.data || [];
  },
};

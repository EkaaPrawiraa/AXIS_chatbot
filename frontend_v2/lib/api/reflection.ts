import { apiClient } from './client';
import { Reflection, CBTSession, ID } from '@/models';
import { API_ROUTES } from '../constants';

export const reflectionAPI = {
  getReflections: async (userId: ID) => {
    const response = await apiClient.get<Reflection[]>(API_ROUTES.REFLECTIONS, {
      params: { userId },
    });
    return response.data.data || [];
  },

  getReflection: async (reflectionId: ID) => {
    const url = API_ROUTES.REFLECTION_DETAIL.replace(':id', reflectionId);
    const response = await apiClient.get<Reflection>(url);
    return response.data.data!;
  },

  submitReflection: async (userId: ID, reflection: Partial<Reflection>) => {
    const response = await apiClient.post<Reflection>(API_ROUTES.REFLECTIONS, {
      userId,
      ...reflection,
    });
    return response.data.data!;
  },

  updateReflection: async (reflectionId: ID, reflection: Partial<Reflection>) => {
    const url = API_ROUTES.REFLECTION_DETAIL.replace(':id', reflectionId);
    const response = await apiClient.patch<Reflection>(url, reflection);
    return response.data.data!;
  },

  deleteReflection: async (reflectionId: ID) => {
    const url = API_ROUTES.REFLECTION_DETAIL.replace(':id', reflectionId);
    const response = await apiClient.delete(url);
    return response.data.success;
  },

  analyzeCBT: async (cbtSession: Partial<CBTSession>) => {
    const response = await apiClient.post<{ analysis: string }>(
      '/reflections/analyze-cbt',
      cbtSession
    );
    return response.data.data?.analysis || '';
  },
};

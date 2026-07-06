import { apiClient } from './client';
import { Memory, CreateMemoryRequest, UpdateMemoryRequest, ID } from '@/models';
import { API_ROUTES } from '../constants';

export const memoryAPI = {
  getMemories: async (userId: ID, filters?: any) => {
    const response = await apiClient.get<Memory[]>(API_ROUTES.MEMORIES, {
      params: { userId, ...filters },
    });
    return response.data.data || [];
  },

  getMemory: async (memoryId: ID) => {
    const url = API_ROUTES.MEMORY_DETAIL.replace(':id', memoryId);
    const response = await apiClient.get<Memory>(url);
    return response.data.data!;
  },

  createMemory: async (userId: ID, request: CreateMemoryRequest) => {
    const response = await apiClient.post<Memory>(API_ROUTES.MEMORIES, {
      userId,
      ...request,
    });
    return response.data.data!;
  },

  updateMemory: async (memoryId: ID, request: UpdateMemoryRequest) => {
    const url = API_ROUTES.MEMORY_DETAIL.replace(':id', memoryId);
    const response = await apiClient.patch<Memory>(url, request);
    return response.data.data!;
  },

  deleteMemory: async (memoryId: ID) => {
    const url = API_ROUTES.MEMORY_DETAIL.replace(':id', memoryId);
    const response = await apiClient.delete(url);
    return response.data.success;
  },

  togglePin: async (memoryId: ID, isPinned: boolean) => {
    const url = API_ROUTES.MEMORY_DETAIL.replace(':id', memoryId);
    const response = await apiClient.patch<Memory>(url, { isPinned });
    return response.data.data!;
  },
};

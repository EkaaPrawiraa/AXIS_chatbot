import { apiClient } from './client';
import {
  Memory,
  CreateMemoryRequest,
  MemoryGraphRelationListResponse,
  MemoryNodeListResponse,
  MemoryNodeType,
  MemoryResetResponse,
  UpdateMemoryNodeRequest,
  UpdateMemoryRequest,
  ID,
} from '@/models';
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

  getMemoryNodes: async (userId: ID, nodeType: MemoryNodeType, searchQuery?: string) => {
    const response = await apiClient.get<MemoryNodeListResponse>('/memories/kg', {
      params: { userId, nodeType, searchQuery },
    });
    return response.data.data!;
  },

  getMemoryRelations: async (userId: ID, limit: number = 150) => {
    const response = await apiClient.get<MemoryGraphRelationListResponse>('/memories/kg/relations', {
      params: { userId, limit },
    });
    return response.data.data!;
  },

  updateMemoryNode: async (
    userId: ID,
    nodeType: MemoryNodeType,
    nodeId: ID,
    request: UpdateMemoryNodeRequest
  ) => {
    const response = await apiClient.patch(`/memories/kg/${nodeType}/${nodeId}`, {
      userId,
      ...request,
    });
    return response.data.data!;
  },

  deleteMemoryNode: async (userId: ID, nodeType: MemoryNodeType, nodeId: ID) => {
    const response = await apiClient.delete(`/memories/kg/${nodeType}/${nodeId}`, {
      params: { userId },
    });
    return response.data.data!;
  },

  resetUserMemory: async (userId: ID) => {
    const response = await apiClient.delete<MemoryResetResponse>('/memories/kg/reset', {
      params: { userId },
    });
    return response.data.data!;
  },
};

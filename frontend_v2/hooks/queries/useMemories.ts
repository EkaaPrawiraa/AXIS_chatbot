import { useQuery } from '@tanstack/react-query';
import { memoryAPI } from '@/lib/api/memory';
import { Memory, MemoryFilter, MemoryGraphRelationListResponse, MemoryNodeListResponse, MemoryNodeType, ID } from '@/models';

export function useMemories(userId: ID | null, filters?: MemoryFilter, enabled: boolean = true) {
  return useQuery<Memory[]>({
    queryKey: ['memories', userId, filters],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return memoryAPI.getMemories(userId, filters);
    },
    enabled: !!userId && enabled,
  });
}

export function useMemory(memoryId: ID | null, enabled: boolean = true) {
  return useQuery<Memory>({
    queryKey: ['memory', memoryId],
    queryFn: () => {
      if (!memoryId) throw new Error('Memory ID is required');
      return memoryAPI.getMemory(memoryId);
    },
    enabled: !!memoryId && enabled,
  });
}

export function useMemoryRelations(userId: ID | null, limit: number = 150, enabled: boolean = true) {
  return useQuery<MemoryGraphRelationListResponse>({
    queryKey: ['memory-relations', userId, limit],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return memoryAPI.getMemoryRelations(userId, limit);
    },
    enabled: !!userId && enabled,
  });
}

export function useMemoryNodes(
  userId: ID | null,
  nodeType: MemoryNodeType,
  searchQuery: string = '',
  enabled: boolean = true
) {
  return useQuery<MemoryNodeListResponse>({
    queryKey: ['memory-nodes', userId, nodeType, searchQuery],
    queryFn: () => {
      if (!userId) throw new Error('User ID is required');
      return memoryAPI.getMemoryNodes(userId, nodeType, searchQuery);
    },
    enabled: !!userId && enabled,
  });
}

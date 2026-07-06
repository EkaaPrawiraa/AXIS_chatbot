import { useMutation, useQueryClient } from '@tanstack/react-query';
import { memoryAPI } from '@/lib/api/memory';
import { CreateMemoryRequest, MemoryNodeType, UpdateMemoryNodeRequest, UpdateMemoryRequest, ID } from '@/models';

export function useCreateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, request }: { userId: ID; request: CreateMemoryRequest }) =>
      memoryAPI.createMemory(userId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
}

export function useUpdateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ memoryId, request }: { memoryId: ID; request: UpdateMemoryRequest }) =>
      memoryAPI.updateMemory(memoryId, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['memory', data.id] });
    },
  });
}

export function useDeleteMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memoryId: ID) => memoryAPI.deleteMemory(memoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
    },
  });
}

export function useTogglePinMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ memoryId, isPinned }: { memoryId: ID; isPinned: boolean }) =>
      memoryAPI.togglePin(memoryId, isPinned),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['memory', data.id] });
    },
  });
}

export function useUpdateMemoryNode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      nodeType,
      nodeId,
      request,
    }: {
      userId: ID;
      nodeType: MemoryNodeType;
      nodeId: ID;
      request: UpdateMemoryNodeRequest;
    }) => memoryAPI.updateMemoryNode(userId, nodeType, nodeId, request),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['memory-nodes', variables.userId] });
    },
  });
}

export function useDeleteMemoryNode() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, nodeType, nodeId }: { userId: ID; nodeType: MemoryNodeType; nodeId: ID }) =>
      memoryAPI.deleteMemoryNode(userId, nodeType, nodeId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['memory-nodes', variables.userId] });
    },
  });
}

export function useResetUserMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId }: { userId: ID }) => memoryAPI.resetUserMemory(userId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['memory-nodes', variables.userId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph', variables.userId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph-relations', variables.userId] });
      queryClient.invalidateQueries({ queryKey: ['memories', variables.userId] });
    },
  });
}

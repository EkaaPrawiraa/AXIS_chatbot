import { useMutation, useQueryClient } from '@tanstack/react-query';
import { memoryAPI } from '@/lib/api/memory';
import { CreateMemoryRequest, UpdateMemoryRequest, ID } from '@/models';

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

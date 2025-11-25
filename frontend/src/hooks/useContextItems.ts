// src/hooks/useContextItems.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getContext,
  addContextItems,
  updateContextItem,
  removeContextItem,
} from "../lib/cortexApi";
import type { ContextItem, ContextBudget } from "../domain/types";

export const contextQueryKey = (projectId: string) =>
  ["context", { projectId }] as const;

export function useContextBudget(projectId: string) {
  const query = useQuery({
    queryKey: contextQueryKey(projectId),
    queryFn: () => getContext(projectId),
    enabled: !!projectId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useAddContextItems(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: { items: ContextItem[] }) => addContextItems(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextQueryKey(projectId) });
    },
  });

  return mutation;
}

export function useUpdateContextItem(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: Partial<ContextItem> }) =>
      updateContextItem(projectId, itemId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextQueryKey(projectId) });
    },
  });

  return mutation;
}

export function useRemoveContextItem(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (itemId: string) => removeContextItem(projectId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextQueryKey(projectId) });
    },
  });

  return mutation;
}

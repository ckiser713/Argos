// src/hooks/useContextItems.ts
import { useQuery } from "@tanstack/react-query";
import { getContext } from "../lib/cortexApi";
import type { ContextItem, ContextBudget } from "../domain/types";

export interface UseContextItemsResult {
  items: ContextItem[];
  budget: ContextBudget;
}

export const contextQueryKey = (projectId?: string) =>
  ["context", { projectId }] as const;

export async function fetchContext(projectId?: string): Promise<UseContextItemsResult> {
  return getContext(projectId);
}

/**
 * Fetch working context (items + budget) for Deep Research / StrategyDeck panels.
 */
export function useContextItems(projectId?: string) {
  const query = useQuery({
    queryKey: contextQueryKey(projectId),
    queryFn: () => fetchContext(projectId),
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

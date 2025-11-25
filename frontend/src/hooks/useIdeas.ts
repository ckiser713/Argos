// src/hooks/useIdeas.ts
import { useQuery } from "@tanstack/react-query";
import { listIdeas } from "../lib/cortexApi";
import type { IdeaTicket } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export type UseIdeasResult = PaginatedResponse<IdeaTicket>;

export interface UseIdeasOptions {
  projectId?: string;
  status?: string;
}

export const ideasQueryKey = (opts: UseIdeasOptions = {}) =>
  ["ideas", { projectId: opts.projectId, status: opts.status }] as const;

export async function fetchIdeas(opts: UseIdeasOptions = {}): Promise<UseIdeasResult> {
  const { projectId, status } = opts;
  return listIdeas({ projectId, status });
}

/**
 * Fetch idea tickets (Idea Station).
 */
export function useIdeas(opts: UseIdeasOptions = {}) {
  const query = useQuery({
    queryKey: ideasQueryKey(opts),
    queryFn: () => fetchIdeas(opts),
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

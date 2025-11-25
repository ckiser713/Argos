// src/hooks/useAgentRuns.ts
import { useQuery } from "@tanstack/react-query";
import { listAgentRuns } from "../lib/cortexApi";
import type { AgentRun } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export type UseAgentRunsResult = PaginatedResponse<AgentRun>;

export const agentRunsQueryKey = (projectId?: string) =>
  ["agentRuns", { projectId }] as const;

export async function fetchAgentRuns(
  projectId?: string
): Promise<UseAgentRunsResult> {
  return listAgentRuns({ projectId });
}

/**
 * Fetch agent runs (e.g., for Mission Control / Deep Research history).
 */
export function useAgentRuns(projectId?: string) {
  const query = useQuery({
    queryKey: agentRunsQueryKey(projectId),
    queryFn: () => fetchAgentRuns(projectId),
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

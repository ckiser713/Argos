// src/hooks/useAgentRuns.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listAgentRuns,
  getAgentRun,
  startAgentRun,
  cancelAgentRun,
  listAgentRunSteps,
  listAgentRunMessages,
  appendAgentRunMessage,
  listAgentRunNodeStates,
} from "../lib/cortexApi";
import type { AgentRun, AgentStep, AgentMessage, AgentNodeState, StartAgentRunRequest } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export const agentRunsQueryKey = (projectId: string) =>
  ["agentRuns", { projectId }] as const;

export const agentRunQueryKey = (projectId: string, runId: string) =>
  ["agentRun", { projectId, runId }] as const;

export const agentRunStepsQueryKey = (projectId: string, runId: string) =>
  ["agentRunSteps", { projectId, runId }] as const;

export const agentRunMessagesQueryKey = (projectId: string, runId: string) =>
  ["agentRunMessages", { projectId, runId }] as const;

export const agentRunNodeStatesQueryKey = (projectId: string, runId: string) =>
  ["agentRunNodeStates", { projectId, runId }] as const;

export function useAgentRuns(projectId: string) {
  const query = useQuery({
    queryKey: agentRunsQueryKey(projectId),
    queryFn: () => listAgentRuns(projectId),
    enabled: !!projectId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useAgentRun(projectId: string, runId: string) {
  const query = useQuery({
    queryKey: agentRunQueryKey(projectId, runId),
    queryFn: () => getAgentRun(projectId, runId),
    enabled: !!projectId && !!runId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useStartAgentRun(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: StartAgentRunRequest) => startAgentRun(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentRunsQueryKey(projectId) });
    },
  });

  return mutation;
}

// Alias for compatibility
export const useCreateAgentRun = useStartAgentRun;

export function useCancelAgentRun(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (runId: string) => cancelAgentRun(projectId, runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: agentRunsQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: agentRunQueryKey(projectId, runId) });
    },
  });

  return mutation;
}

export function useAgentRunSteps(projectId: string, runId: string, params?: { cursor?: string; limit?: number }) {
  const query = useQuery({
    queryKey: agentRunStepsQueryKey(projectId, runId),
    queryFn: () => listAgentRunSteps(projectId, runId, params),
    enabled: !!projectId && !!runId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useAgentRunMessages(projectId: string, runId: string, params?: { cursor?: string; limit?: number }) {
  const query = useQuery({
    queryKey: agentRunMessagesQueryKey(projectId, runId),
    queryFn: () => listAgentRunMessages(projectId, runId, params),
    enabled: !!projectId && !!runId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useAppendAgentRunMessage(projectId: string, runId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: { content: string; contextItemIds?: string[] }) =>
      appendAgentRunMessage(projectId, runId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentRunMessagesQueryKey(projectId, runId) });
      queryClient.invalidateQueries({ queryKey: agentRunQueryKey(projectId, runId) });
    },
  });

  return mutation;
}

export function useAgentRunNodeStates(projectId: string, runId: string) {
  const query = useQuery({
    queryKey: agentRunNodeStatesQueryKey(projectId, runId),
    queryFn: () => listAgentRunNodeStates(projectId, runId),
    enabled: !!projectId && !!runId,
    refetchInterval: 2000, // Poll every 2 seconds for updates
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// Export streaming hook
export { useAgentStream } from "./useAgentStream";
export type { AgentStreamEvent, UseAgentStreamOptions } from "./useAgentStream";

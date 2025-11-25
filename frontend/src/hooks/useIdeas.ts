// src/hooks/useIdeas.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listIdeaCandidates,
  createIdeaCandidate,
  updateIdeaCandidate,
  listIdeaClusters,
  createIdeaCluster,
  listIdeaTickets,
  createIdeaTicket,
} from "../lib/cortexApi";
import type { IdeaTicket, IdeaCandidate, IdeaCluster } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export type UseIdeasResult = PaginatedResponse<IdeaTicket>;

export interface UseIdeasOptions {
  projectId?: string;
  status?: string;
}

export const ideasQueryKey = (opts: UseIdeasOptions = {}) =>
  ["ideas", { projectId: opts.projectId, status: opts.status }] as const;

export const ideaCandidatesQueryKey = (projectId?: string, options?: { status?: string; type?: string }) =>
  ["ideaCandidates", { projectId, ...options }] as const;

export const ideaClustersQueryKey = (projectId?: string) =>
  ["ideaClusters", { projectId }] as const;

export const ideaTicketsQueryKey = (projectId?: string, status?: string) =>
  ["ideaTickets", { projectId, status }] as const;

export async function fetchIdeas(opts: UseIdeasOptions = {}): Promise<UseIdeasResult> {
  const { projectId, status } = opts;
  if (!projectId) throw new Error("projectId is required");
  return listIdeaTickets(projectId, { status });
}

/**
 * Fetch idea tickets (Idea Station).
 */
export function useIdeas(opts: UseIdeasOptions = {}) {
  const query = useQuery({
    queryKey: ideasQueryKey(opts),
    queryFn: () => fetchIdeas(opts),
    enabled: !!opts.projectId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * List idea candidates.
 */
export function useIdeaCandidates(projectId?: string, options?: { status?: string; type?: string }) {
  const query = useQuery({
    queryKey: ideaCandidatesQueryKey(projectId, options),
    queryFn: () => {
      if (!projectId) throw new Error("projectId is required for useIdeaCandidates");
      return listIdeaCandidates(projectId, options);
    },
    enabled: !!projectId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Create an idea candidate.
 */
export function useCreateIdeaCandidate(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<IdeaCandidate>) => createIdeaCandidate(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ideaCandidatesQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Update an idea candidate.
 */
export function useUpdateIdeaCandidate(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ candidateId, payload }: { candidateId: string; payload: Partial<IdeaCandidate> }) =>
      updateIdeaCandidate(projectId, candidateId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ideaCandidatesQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * List idea clusters.
 */
export function useIdeaClusters(projectId?: string) {
  const query = useQuery({
    queryKey: ideaClustersQueryKey(projectId),
    queryFn: () => {
      if (!projectId) throw new Error("projectId is required for useIdeaClusters");
      return listIdeaClusters(projectId);
    },
    enabled: !!projectId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Create an idea cluster.
 */
export function useCreateIdeaCluster(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<IdeaCluster>) => createIdeaCluster(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ideaClustersQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * List idea tickets.
 */
export function useIdeaTickets(projectId?: string, status?: string) {
  const query = useQuery({
    queryKey: ideaTicketsQueryKey(projectId, status),
    queryFn: () => {
      if (!projectId) throw new Error("projectId is required for useIdeaTickets");
      return listIdeaTickets(projectId, { status });
    },
    enabled: !!projectId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Create an idea ticket.
 */
export function useCreateIdeaTicket(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<IdeaTicket>) => createIdeaTicket(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ideaTicketsQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: ideasQueryKey({ projectId }) });
    },
  });

  return mutation;
}

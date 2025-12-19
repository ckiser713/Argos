// src/hooks/useIngestJobs.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listIngestJobs,
  getIngestJob,
  createIngestJob,
  cancelIngestJob,
  deleteIngestJob,
} from "../lib/argosApi";
import type { IngestJob, CreateIngestJobRequest } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export type UseIngestJobsResult = PaginatedResponse<IngestJob>;

export const ingestJobsQueryKey = (projectId: string) =>
  ["ingestJobs", { projectId }] as const;

export const ingestJobQueryKey = (projectId: string, jobId: string) =>
  ["ingestJob", { projectId, jobId }] as const;

export async function fetchIngestJobs(
  projectId: string,
  params?: { status?: string; stage?: string; sourceId?: string; cursor?: string; limit?: number }
): Promise<UseIngestJobsResult> {
  return listIngestJobs({ projectId, ...params });
}

/**
 * Fetch ingest jobs for a given project.
 * Automatically polls for updates when there are running/pending jobs.
 */
export function useIngestJobs(
  projectId: string,
  params?: { status?: string; stage?: string; sourceId?: string; cursor?: string; limit?: number }
) {
  const query = useQuery({
    queryKey: ingestJobsQueryKey(projectId),
    queryFn: () => fetchIngestJobs(projectId, params),
    enabled: !!projectId,
    // Poll every 3 seconds if there are running/pending jobs
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data?.items) return false;
      // Check if any jobs are running or pending
      const hasActiveJobs = data.items.some(
        job => job.status === 'running' || job.status === 'pending'
      );
      return hasActiveJobs ? 3000 : false; // Poll every 3 seconds if active jobs exist
    },
    // Refetch when window regains focus
    refetchOnWindowFocus: true,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Fetch a single ingest job.
 * Automatically polls for updates when the job is running/pending.
 */
export function useIngestJob(projectId: string, jobId: string) {
  const query = useQuery({
    queryKey: ingestJobQueryKey(projectId, jobId),
    queryFn: () => getIngestJob(projectId, jobId),
    enabled: !!projectId && !!jobId,
    // Poll every 2 seconds if job is running or pending
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      return (data.status === 'running' || data.status === 'pending') ? 2000 : false;
    },
    // Refetch when window regains focus
    refetchOnWindowFocus: true,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useCreateIngestJob(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (newJob: CreateIngestJobRequest) => createIngestJob(projectId, newJob),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ingestJobsQueryKey(projectId) });
    },
  });

  return mutation;
}

export function useCancelIngestJob(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (jobId: string) => cancelIngestJob(projectId, jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ingestJobsQueryKey(projectId) });
    },
  });

  return mutation;
}

export function useDeleteIngestJob(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (jobId: string) => deleteIngestJob(projectId, jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ingestJobsQueryKey(projectId) });
    },
  });

  return mutation;
}

// src/hooks/useIngestJobs.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listIngestJobs,
  getIngestJob,
  createIngestJob,
  cancelIngestJob,
  deleteIngestJob,
} from "../lib/cortexApi";
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
 */
export function useIngestJobs(
  projectId: string,
  params?: { status?: string; stage?: string; sourceId?: string; cursor?: string; limit?: number }
) {
  const query = useQuery({
    queryKey: ingestJobsQueryKey(projectId),
    queryFn: () => fetchIngestJobs(projectId, params),
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
 * Fetch a single ingest job.
 */
export function useIngestJob(projectId: string, jobId: string) {
  const query = useQuery({
    queryKey: ingestJobQueryKey(projectId, jobId),
    queryFn: () => getIngestJob(projectId, jobId),
    enabled: !!projectId && !!jobId,
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

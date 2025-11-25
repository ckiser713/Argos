// src/hooks/useIngestJobs.ts
import { useQuery } from "@tanstack/react-query";
import { listIngestJobs } from "../lib/cortexApi";
import type { IngestJob } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export type UseIngestJobsResult = PaginatedResponse<IngestJob>;

export const ingestJobsQueryKey = (projectId?: string) =>
  ["ingestJobs", { projectId }] as const;

export async function fetchIngestJobs(
  projectId?: string
): Promise<UseIngestJobsResult> {
  return listIngestJobs({ projectId });
}

/**
 * Fetch ingest jobs for a given project.
 * If projectId is undefined, it returns all jobs visible to the user (per backend contract).
 */
export function useIngestJobs(projectId?: string) {
  const query = useQuery({
    queryKey: ingestJobsQueryKey(projectId),
    queryFn: () => fetchIngestJobs(projectId),
    enabled: projectId !== undefined && projectId !== null,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

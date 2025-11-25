// src/hooks/useRoadmap.ts
import { useQuery } from "@tanstack/react-query";
import { fetchRoadmap } from "../lib/cortexApi";
import type { RoadmapNode, RoadmapEdge } from "../domain/types";

export interface UseRoadmapResult {
  nodes: RoadmapNode[];
  edges: RoadmapEdge[];
}

export const roadmapQueryKey = (projectId?: string) =>
  ["roadmap", { projectId }] as const;

export async function fetchRoadmapForProject(
  projectId: string
): Promise<UseRoadmapResult> {
  return fetchRoadmap({ projectId });
}

/**
 * Fetch roadmap / workflow graph for the given project.
 */
export function useRoadmap(projectId?: string) {
  const query = useQuery({
    queryKey: roadmapQueryKey(projectId),
    queryFn: () => {
      if (!projectId) throw new Error("projectId is required for useRoadmap");
      return fetchRoadmapForProject(projectId);
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

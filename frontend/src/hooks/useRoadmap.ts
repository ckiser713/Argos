// src/hooks/useRoadmap.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchRoadmap,
  generateRoadmap,
  listRoadmapNodes,
  createRoadmapNode,
  updateRoadmapNode,
  deleteRoadmapNode,
  createRoadmapEdge,
  deleteRoadmapEdge,
} from "../lib/argosApi";
import type { RoadmapNode, RoadmapEdge, RoadmapGraph } from "../domain/types";
import type { PaginatedResponse } from "../domain/api-types";

export interface UseRoadmapResult {
  nodes: RoadmapNode[];
  edges: RoadmapEdge[];
}

export const roadmapQueryKey = (projectId?: string) =>
  ["roadmap", { projectId }] as const;

export const roadmapNodesQueryKey = (projectId?: string, options?: { status?: string; laneId?: string }) =>
  ["roadmapNodes", { projectId, ...options }] as const;

export async function fetchRoadmapForProject(
  projectId: string
): Promise<UseRoadmapResult> {
  const graph = await fetchRoadmap(projectId);
  return {
    nodes: graph.nodes || [],
    edges: graph.edges || [],
  };
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

/**
 * List roadmap nodes with filtering.
 */
export function useRoadmapNodes(
  projectId?: string,
  options?: { status?: string; laneId?: string; cursor?: string; limit?: number }
) {
  const query = useQuery({
    queryKey: roadmapNodesQueryKey(projectId, options),
    queryFn: () => {
      if (!projectId) throw new Error("projectId is required for useRoadmapNodes");
      return listRoadmapNodes(projectId, options);
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
 * Create a roadmap node.
 */
export function useCreateRoadmapNode(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<RoadmapNode>) => createRoadmapNode(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roadmapQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: roadmapNodesQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Update a roadmap node.
 */
export function useUpdateRoadmapNode(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ nodeId, payload }: { nodeId: string; payload: Partial<RoadmapNode> }) =>
      updateRoadmapNode(projectId, nodeId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roadmapQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: roadmapNodesQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Delete a roadmap node.
 */
export function useDeleteRoadmapNode(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (nodeId: string) => deleteRoadmapNode(projectId, nodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roadmapQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: roadmapNodesQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Create a roadmap edge.
 */
export function useCreateRoadmapEdge(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<RoadmapEdge>) => createRoadmapEdge(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roadmapQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Delete a roadmap edge.
 */
export function useDeleteRoadmapEdge(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (edgeId: string) => deleteRoadmapEdge(projectId, edgeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roadmapQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Generate roadmap from project intent.
 */
export function useGenerateRoadmap(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (params: { intent?: string; useExistingIdeas?: boolean }) =>
      generateRoadmap(projectId, params.intent, params.useExistingIdeas ?? true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roadmapQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: roadmapNodesQueryKey(projectId) });
    },
  });

  return mutation;
}

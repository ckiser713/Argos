// src/hooks/useKnowledgeGraph.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchKnowledgeGraph,
  getKnowledgeNode,
  getKnowledgeNodeNeighbors,
  createKnowledgeNode,
  updateKnowledgeNode,
  createKnowledgeEdge,
  deleteKnowledgeEdge,
  searchKnowledge,
} from "../lib/cortexApi";
import type { KnowledgeNode, KnowledgeEdge, KnowledgeGraph } from "../domain/types";

export interface UseKnowledgeGraphResult {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export const knowledgeGraphQueryKey = (projectId?: string, options?: { view?: string; focusNodeId?: string }) =>
  ["knowledgeGraph", { projectId, ...options }] as const;

export const knowledgeNodeQueryKey = (projectId?: string, nodeId?: string) =>
  ["knowledgeNode", { projectId, nodeId }] as const;

export const knowledgeNodeNeighborsQueryKey = (projectId?: string, nodeId?: string) =>
  ["knowledgeNodeNeighbors", { projectId, nodeId }] as const;

export async function fetchKnowledgeGraphForProject(
  projectId?: string,
  options?: { view?: string; focusNodeId?: string }
): Promise<KnowledgeGraph> {
  if (!projectId) throw new Error("projectId is required");
  return fetchKnowledgeGraph(projectId, options);
}

/**
 * Fetch knowledge graph for Knowledge Nexus.
 */
export function useKnowledgeGraph(projectId?: string, options?: { view?: string; focusNodeId?: string }) {
  const query = useQuery({
    queryKey: knowledgeGraphQueryKey(projectId, options),
    queryFn: () => fetchKnowledgeGraphForProject(projectId, options),
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
 * Get a single knowledge node.
 */
export function useKnowledgeNode(projectId?: string, nodeId?: string) {
  const query = useQuery({
    queryKey: knowledgeNodeQueryKey(projectId, nodeId),
    queryFn: () => {
      if (!projectId || !nodeId) throw new Error("projectId and nodeId are required");
      return getKnowledgeNode(projectId, nodeId);
    },
    enabled: !!projectId && !!nodeId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Get neighbors for a knowledge node.
 */
export function useKnowledgeNodeNeighbors(projectId?: string, nodeId?: string) {
  const query = useQuery({
    queryKey: knowledgeNodeNeighborsQueryKey(projectId, nodeId),
    queryFn: () => {
      if (!projectId || !nodeId) throw new Error("projectId and nodeId are required");
      return getKnowledgeNodeNeighbors(projectId, nodeId);
    },
    enabled: !!projectId && !!nodeId,
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Create a knowledge node.
 */
export function useCreateKnowledgeNode(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<KnowledgeNode>) => createKnowledgeNode(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeGraphQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Update a knowledge node.
 */
export function useUpdateKnowledgeNode(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ nodeId, payload }: { nodeId: string; payload: Partial<KnowledgeNode> }) =>
      updateKnowledgeNode(projectId, nodeId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: knowledgeGraphQueryKey(projectId) });
      queryClient.invalidateQueries({ queryKey: knowledgeNodeQueryKey(projectId, variables.nodeId) });
      queryClient.invalidateQueries({ queryKey: knowledgeNodeNeighborsQueryKey(projectId, variables.nodeId) });
    },
  });

  return mutation;
}

/**
 * Create a knowledge edge.
 */
export function useCreateKnowledgeEdge(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: Partial<KnowledgeEdge>) => createKnowledgeEdge(projectId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: knowledgeGraphQueryKey(projectId) });
      // Invalidate neighbors for both source and target nodes
      if (variables.source) {
        queryClient.invalidateQueries({ queryKey: knowledgeNodeNeighborsQueryKey(projectId, variables.source) });
      }
      if (variables.target) {
        queryClient.invalidateQueries({ queryKey: knowledgeNodeNeighborsQueryKey(projectId, variables.target) });
      }
    },
  });

  return mutation;
}

/**
 * Delete a knowledge edge.
 */
export function useDeleteKnowledgeEdge(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (edgeId: string) => deleteKnowledgeEdge(projectId, edgeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeGraphQueryKey(projectId) });
    },
  });

  return mutation;
}

/**
 * Search knowledge nodes.
 */
export function useSearchKnowledge(projectId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (params: { query: string; type?: string; tags?: string[]; limit?: number; useVectorSearch?: boolean }) =>
      searchKnowledge(projectId, params.query, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: knowledgeGraphQueryKey(projectId) });
    },
  });

  return mutation;
}

// src/hooks/useKnowledgeGraph.ts
import { useQuery } from "@tanstack/react-query";
import { fetchKnowledgeGraph } from "../lib/cortexApi";
import type { KnowledgeNode, KnowledgeEdge } from "../domain/types";

export interface UseKnowledgeGraphResult {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export const knowledgeGraphQueryKey = (projectId?: string) =>
  ["knowledgeGraph", { projectId }] as const;

export async function fetchKnowledgeGraphForProject(
  projectId?: string
): Promise<UseKnowledgeGraphResult> {
  return fetchKnowledgeGraph(projectId);
}

/**
 * Fetch knowledge graph for Knowledge Nexus.
 */
export function useKnowledgeGraph(projectId?: string) {
  const query = useQuery({
    queryKey: knowledgeGraphQueryKey(projectId),
    queryFn: () => fetchKnowledgeGraphForProject(projectId),
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

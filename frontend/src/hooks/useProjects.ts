// src/hooks/useProjects.ts
import { useQuery } from "@tanstack/react-query";
import { getProjects } from "../lib/cortexApi";
import type { CortexProject } from "../domain/types";
import { useCortexStore } from "../state/cortexStore";

export const projectsQueryKey = ["projects"] as const;

export async function fetchProjects(): Promise<CortexProject[]> {
  return getProjects();
}

/**
 * Fetches all projects; syncs basic project list into the Cortex store.
 */
export function useProjects() {
  const setProjects = useCortexStore((s) => s.setProjects);

  const query = useQuery({
    queryKey: projectsQueryKey,
    queryFn: async () => {
      const data = await fetchProjects();
      setProjects(data);
      return data;
    },
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Returns the currently selected project based on `currentProjectId` in the store,
 * using React Query’s project data if available.
 */
export function useCurrentProject() {
  const currentProjectId = useCortexStore((s) => s.currentProjectId);
  const projectsFromStore = useCortexStore((s) => s.projects);
  const { data: projectsQueryData } = useQuery({
    queryKey: projectsQueryKey,
    queryFn: fetchProjects,
    // Keep previous data to avoid flicker when switching project
    placeholderData: projectsFromStore.length ? projectsFromStore : undefined,
  });

  const projects = projectsQueryData ?? projectsFromStore;
  const current =
    currentProjectId && projects
      ? projects.find((p) => p.id === currentProjectId) ?? null
      : null;

  return {
    project: current,
    currentProjectId,
  };
}

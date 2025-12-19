// src/hooks/useProjects.ts
import { useQuery } from "@tanstack/react-query";
import { getProjects } from "../lib/cortexApi";
import type { ArgosProject } from "../domain/types";
import { useArgosStore } from "../state/cortexStore";

export const projectsQueryKey = ["projects"] as const;

export async function fetchProjects(): Promise<ArgosProject[]> {
  // #region agent log
  fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'frontend/src/hooks/useProjects.ts:10',message:'Starting fetchProjects call',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion
  try {
    const response = await getProjects();
    // #region agent log
    fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'frontend/src/hooks/useProjects.ts:14',message:'fetchProjects call successful',data:{itemsCount: response.items?.length || 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    return response.items;
  } catch (error) {
    // #region agent log
    fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'frontend/src/hooks/useProjects.ts:18',message:'fetchProjects call failed',data:{error: error?.message || 'Unknown error', errorType: error?.name || 'Unknown'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    throw error;
  }
}

/**
 * Fetches all projects; syncs basic project list into the Argos store.
 */
export function useProjects() {
  const setProjects = useArgosStore((s) => s.setProjects);

  const query = useQuery({
    queryKey: projectsQueryKey,
    queryFn: async () => {
      // #region agent log
      fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'frontend/src/hooks/useProjects.ts:27',message:'useProjects queryFn starting',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      console.log('[DEBUG] useProjects: Starting fetchProjects');
      const data = await fetchProjects();
      console.log('[DEBUG] useProjects: fetchProjects complete, setting projects in store', data?.length);
      setProjects(data);
      // #region agent log
      fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'frontend/src/hooks/useProjects.ts:34',message:'useProjects queryFn completed successfully',data:{projectsCount: data?.length || 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      return data;
    },
  });

  console.log('[DEBUG] useProjects: query state', { isLoading: query.isLoading, isFetching: query.isFetching, hasData: !!query.data });

  // #region agent log
  fetch('http://localhost:7243/ingest/22b2bc10-668b-4e25-b7af-89ca2a3e5432',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'frontend/src/hooks/useProjects.ts:39',message:'useProjects hook render',data:{isLoading: query.isLoading, isError: !!query.error, hasData: !!query.data, errorMessage: query.error?.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion

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
  const currentProjectId = useArgosStore((s) => s.currentProjectId);
  const projectsFromStore = useArgosStore((s) => s.projects);
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

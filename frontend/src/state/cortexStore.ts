// src/state/cortexStore.ts
import { create } from "zustand";
import type { CortexProject } from "../domain/types";

export interface CortexStoreState {
  currentProjectId: string | null;
  projects: CortexProject[]; // optional cache/override; React Query is source of truth
  setCurrentProjectId: (projectId: string | null) => void;
  setProjects: (projects: CortexProject[]) => void;
  upsertProject: (project: CortexProject) => void;
}

export const useCortexStore = create<CortexStoreState>((set) => ({
  currentProjectId: null,
  projects: [],
  setCurrentProjectId: (projectId) => set({ currentProjectId: projectId }),
  setProjects: (projects) => set({ projects }),
  upsertProject: (project) =>
    set((state) => {
      const existingIndex = state.projects.findIndex((p) => p.id === project.id);
      if (existingIndex === -1) {
        return { projects: [...state.projects, project] };
      }
      const next = [...state.projects];
      next[existingIndex] = project;
      return { projects: next };
    }),
}));

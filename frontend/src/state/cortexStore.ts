// src/state/argosStore.ts
import { create } from "zustand";
import type { ArgosProject } from "../domain/types";

export interface ArgosStoreState {
  currentProjectId: string | null;
  projects: ArgosProject[]; // optional cache/override; React Query is source of truth
  setCurrentProjectId: (projectId: string | null) => void;
  setProjects: (projects: ArgosProject[]) => void;
  upsertProject: (project: ArgosProject) => void;
}

export const useArgosStore = create<ArgosStoreState>((set) => ({
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

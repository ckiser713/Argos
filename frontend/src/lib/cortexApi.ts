/**
 * Typed API client for the Cortex backend.
 *
 * This module is the ONLY place that knows concrete URL paths and payload shapes.
 * React hooks / stores should depend on these functions instead of `fetch` directly.
 */

import { http } from "./http";

import type {
  CortexProject,
  IngestJob,
  IngestJobStatus,
  RoadmapNode,
  RoadmapEdge,
  AgentRun,
  IdeaTicket,
  KnowledgeNode,
  KnowledgeEdge,
  ContextItem,
  ContextBudget,
} from "../domain/types";

import type {
  PaginatedResponse,
  // Project DTOs
  CreateProjectRequest,
  // Ingest DTOs
  CreateIngestJobRequest,
  // Agent DTOs
  StartAgentRunRequest,
  // Context DTOs
  UpdateContextRequest,
} from "../domain/api-types";

/** Utility type for pagination parameters passed from UI. */
export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

/* ============================================================================
 * Projects
 * ==========================================================================*/

/** Fetch all projects visible to the current user. */
export async function getProjects(): Promise<CortexProject[]> {
  return http<CortexProject[]>("/api/projects", {
    method: "GET",
  });
}

/** Fetch a single project by id. */
export async function getProject(projectId: string): Promise<CortexProject> {
  return http<CortexProject>(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: "GET",
  });
}

/** Create a new project. */
export async function createProject(
  payload: CreateProjectRequest
): Promise<CortexProject> {
  return http<CortexProject>("/api/projects", {
    method: "POST",
    body: payload,
  });
}

/* ============================================================================
 * Ingest / Doc Atlas
 * ==========================================================================*/

export interface ListIngestJobsParams extends PaginationParams {
  projectId?: string;
  status?: IngestJobStatus;
  sourceId?: string;
}

/** List ingest jobs, optionally filtered by project / status / source. */
export async function listIngestJobs(
  params: ListIngestJobsParams = {}
): Promise<PaginatedResponse<IngestJob>> {
  const { projectId, status, sourceId, page, pageSize } = params;

  return http<PaginatedResponse<IngestJob>>("/api/ingest/jobs", {
    method: "GET",
    query: {
      projectId,
      status,
      sourceId,
      page,
      pageSize,
    },
  });
}

/** Fetch a single ingest job by id. */
export async function getIngestJob(jobId: string): Promise<IngestJob> {
  return http<IngestJob>(`/api/ingest/jobs/${encodeURIComponent(jobId)}`, {
    method: "GET",
  });
}

/** Create a new ingest job (e.g., uploading files or connecting a source). */
export async function createIngestJob(
  payload: CreateIngestJobRequest
): Promise<IngestJob> {
  return http<IngestJob>("/api/ingest/jobs", {
    method: "POST",
    body: payload,
  });
}

/* ============================================================================
 * Roadmap / Workflow graph
 * ==========================================================================*/

export interface FetchRoadmapParams {
  projectId: string;
}

export interface RoadmapGraph {
  nodes: RoadmapNode[];
  edges: RoadmapEdge[];
}

/** Fetch the roadmap / workflow graph for a project. */
export async function fetchRoadmap(
  params: FetchRoadmapParams
): Promise<RoadmapGraph> {
  const { projectId } = params;

  return http<RoadmapGraph>("/api/roadmap", {
    method: "GET",
    query: { projectId },
  });
}

/* ============================================================================
 * Agent runs
 * ==========================================================================*/

export interface ListAgentRunsParams extends PaginationParams {
  projectId?: string;
}

/** List agent runs, newest first. */
export async function listAgentRuns(
  params: ListAgentRunsParams = {}
): Promise<PaginatedResponse<AgentRun>> {
  const { projectId, page, pageSize } = params;

  return http<PaginatedResponse<AgentRun>>("/api/agents/runs", {
    method: "GET",
    query: {
      projectId,
      page,
      pageSize,
    },
  });
}

/** Fetch a single agent run. */
export async function getAgentRun(runId: string): Promise<AgentRun> {
  return http<AgentRun>(`/api/agents/runs/${encodeURIComponent(runId)}`, {
    method: "GET",
  });
}

/** Start a new agent run. */
export async function startAgentRun(
  payload: StartAgentRunRequest
): Promise<AgentRun> {
  return http<AgentRun>("/api/agents/runs", {
    method: "POST",
    body: payload,
  });
}

/* ============================================================================
 * Ideas / Idea Station
 * ==========================================================================*/

export interface ListIdeasParams extends PaginationParams {
  projectId?: string;
  /** Optional filter by status (e.g., open / in-progress / done) */
  status?: string;
}

/** List idea tickets for the current project / global cortex. */
export async function listIdeas(
  params: ListIdeasParams = {}
): Promise<PaginatedResponse<IdeaTicket>> {
  const { projectId, status, page, pageSize } = params;

  return http<PaginatedResponse<IdeaTicket>>("/api/ideas", {
    method: "GET",
    query: {
      projectId,
      status,
      page,
      pageSize,
    },
  });
}

/** Fetch a single idea ticket. */
export async function getIdeaTicket(id: string): Promise<IdeaTicket> {
  return http<IdeaTicket>(`/api/ideas/${encodeURIComponent(id)}`, {
    method: "GET",
  });
}

/** Partial update to an idea ticket (status, priority, labels, etc.). */
export async function updateIdeaTicket(
  id: string,
  patch: Partial<IdeaTicket>
): Promise<IdeaTicket> {
  return http<IdeaTicket>(`/api/ideas/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: patch,
  });
}

/* ============================================================================
 * Knowledge graph / Knowledge Nexus
 * ==========================================================================*/

export interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

/** Fetch the knowledge graph used by Knowledge Nexus. */
export async function fetchKnowledgeGraph(
  projectId?: string
): Promise<KnowledgeGraph> {
  return http<KnowledgeGraph>("/api/knowledge/graph", {
    method: "GET",
    query: {
      projectId,
    },
  });
}

/* ============================================================================
 * Context / Working memory
 * ==========================================================================*/

export interface ContextState {
  items: ContextItem[];
  budget: ContextBudget;
}

/** Fetch the current context / working memory state. */
export async function getContext(projectId?: string): Promise<ContextState> {
  return http<ContextState>("/api/context", {
    method: "GET",
    query: { projectId },
  });
}

/** Replace or adjust context items / budget. */
export async function updateContext(
  payload: UpdateContextRequest
): Promise<ContextState> {
  return http<ContextState>("/api/context", {
    method: "PUT",
    body: payload,
  });
}

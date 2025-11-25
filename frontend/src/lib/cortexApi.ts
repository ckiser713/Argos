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
  AgentStep,
  AgentMessage,
  AgentNodeState,
  IdeaTicket,
  IdeaCandidate,
  IdeaCluster,
  MissionControlTask,
  KnowledgeNode,
  KnowledgeEdge,
  ContextItem,
  ContextBudget,
} from "../domain/types";

import type {
  PaginatedResponse,
  CreateProjectRequest,
  CreateIngestJobRequest,
  StartAgentRunRequest,
  UpdateContextRequest,
} from "../domain/api-types";

/** Utility type for pagination parameters passed from UI. */
export interface PaginationParams {
  cursor?: string;
  limit?: number;
}

/* ============================================================================
 * Projects
 * ==========================================================================*/

/** Fetch all projects visible to the current user. */
export async function getProjects(params?: PaginationParams): Promise<PaginatedResponse<CortexProject>> {
  return http<PaginatedResponse<CortexProject>>("/api/projects", {
    method: "GET",
    query: params,
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
  projectId: string;
  status?: IngestJobStatus;
  stage?: string;
  sourceId?: string;
}

/** List ingest jobs for a project. */
export async function listIngestJobs(
  params: ListIngestJobsParams
): Promise<PaginatedResponse<IngestJob>> {
  const { projectId, status, stage, sourceId, cursor, limit } = params;
  return http<PaginatedResponse<IngestJob>>(
    `/api/projects/${encodeURIComponent(projectId)}/ingest/jobs`,
    {
      method: "GET",
      query: { status, stage, sourceId, cursor, limit },
    }
  );
}

/** Fetch a single ingest job by id. */
export async function getIngestJob(projectId: string, jobId: string): Promise<IngestJob> {
  return http<IngestJob>(
    `/api/projects/${encodeURIComponent(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}`,
    {
      method: "GET",
    }
  );
}

/** Create a new ingest job. */
export async function createIngestJob(
  projectId: string,
  payload: CreateIngestJobRequest
): Promise<IngestJob> {
  return http<IngestJob>(
    `/api/projects/${encodeURIComponent(projectId)}/ingest/jobs`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Cancel an ingest job. */
export async function cancelIngestJob(projectId: string, jobId: string): Promise<IngestJob> {
  return http<IngestJob>(
    `/api/projects/${encodeURIComponent(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}/cancel`,
    {
      method: "POST",
    }
  );
}

/** Delete an ingest job. */
export async function deleteIngestJob(projectId: string, jobId: string): Promise<void> {
  return http<void>(
    `/api/projects/${encodeURIComponent(projectId)}/ingest/jobs/${encodeURIComponent(jobId)}`,
    {
      method: "DELETE",
    }
  );
}

/* ============================================================================
 * Roadmap / Workflow graph
 * ==========================================================================*/

export interface RoadmapGraph {
  nodes: RoadmapNode[];
  edges: RoadmapEdge[];
  generatedAt: string;
}

/** Fetch the roadmap graph for a project. */
export async function fetchRoadmap(projectId: string): Promise<RoadmapGraph> {
  return http<RoadmapGraph>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap`,
    {
      method: "GET",
    }
  );
}

/** List roadmap nodes. */
export async function listRoadmapNodes(
  projectId: string,
  params?: PaginationParams & { status?: string; laneId?: string }
): Promise<PaginatedResponse<RoadmapNode>> {
  return http<PaginatedResponse<RoadmapNode>>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap/nodes`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Create a roadmap node. */
export async function createRoadmapNode(
  projectId: string,
  payload: Partial<RoadmapNode>
): Promise<RoadmapNode> {
  return http<RoadmapNode>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap/nodes`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Update a roadmap node. */
export async function updateRoadmapNode(
  projectId: string,
  nodeId: string,
  payload: Partial<RoadmapNode>
): Promise<RoadmapNode> {
  return http<RoadmapNode>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap/nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "PATCH",
      body: payload,
    }
  );
}

/** Delete a roadmap node. */
export async function deleteRoadmapNode(projectId: string, nodeId: string): Promise<void> {
  return http<void>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap/nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "DELETE",
    }
  );
}

/** Create a roadmap edge. */
export async function createRoadmapEdge(
  projectId: string,
  payload: Partial<RoadmapEdge>
): Promise<RoadmapEdge> {
  return http<RoadmapEdge>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap/edges`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Delete a roadmap edge. */
export async function deleteRoadmapEdge(projectId: string, edgeId: string): Promise<void> {
  return http<void>(
    `/api/projects/${encodeURIComponent(projectId)}/roadmap/edges/${encodeURIComponent(edgeId)}`,
    {
      method: "DELETE",
    }
  );
}

/* ============================================================================
 * Agent runs
 * ==========================================================================*/

/** List agent runs for a project. */
export async function listAgentRuns(
  projectId: string
): Promise<AgentRun[]> {
  return http<AgentRun[]>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs`,
    {
      method: "GET",
    }
  );
}

/** Fetch a single agent run. */
export async function getAgentRun(projectId: string, runId: string): Promise<AgentRun> {
  return http<AgentRun>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs/${encodeURIComponent(runId)}`,
    {
      method: "GET",
    }
  );
}

/** Start a new agent run. */
export async function startAgentRun(
  projectId: string,
  payload: StartAgentRunRequest
): Promise<AgentRun> {
  return http<AgentRun>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Cancel an agent run. */
export async function cancelAgentRun(projectId: string, runId: string): Promise<AgentRun> {
  return http<AgentRun>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs/${encodeURIComponent(runId)}/cancel`,
    {
      method: "POST",
    }
  );
}

/** List steps for an agent run. */
export async function listAgentRunSteps(
  projectId: string,
  runId: string,
  params?: PaginationParams
): Promise<PaginatedResponse<AgentStep>> {
  return http<PaginatedResponse<AgentStep>>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs/${encodeURIComponent(runId)}/steps`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** List messages for an agent run. */
export async function listAgentRunMessages(
  projectId: string,
  runId: string,
  params?: PaginationParams
): Promise<PaginatedResponse<AgentMessage>> {
  return http<PaginatedResponse<AgentMessage>>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs/${encodeURIComponent(runId)}/messages`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Append a message to an agent run. */
export async function appendAgentRunMessage(
  projectId: string,
  runId: string,
  payload: { content: string; contextItemIds?: string[] }
): Promise<AgentMessage> {
  return http<AgentMessage>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs/${encodeURIComponent(runId)}/messages`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** List node states for an agent run. */
export async function listAgentRunNodeStates(
  projectId: string,
  runId: string
): Promise<AgentNodeState[]> {
  return http<AgentNodeState[]>(
    `/api/projects/${encodeURIComponent(projectId)}/agent-runs/${encodeURIComponent(runId)}/node-states`,
    {
      method: "GET",
    }
  );
}

/* ============================================================================
 * Ideas / Idea Station
 * ==========================================================================*/

/** List idea candidates. */
export async function listIdeaCandidates(
  projectId: string,
  params?: PaginationParams & { status?: string; type?: string }
): Promise<PaginatedResponse<IdeaCandidate>> {
  return http<PaginatedResponse<IdeaCandidate>>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/candidates`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Create an idea candidate. */
export async function createIdeaCandidate(
  projectId: string,
  payload: Partial<IdeaCandidate>
): Promise<IdeaCandidate> {
  return http<IdeaCandidate>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/candidates`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Update an idea candidate. */
export async function updateIdeaCandidate(
  projectId: string,
  candidateId: string,
  payload: Partial<IdeaCandidate>
): Promise<IdeaCandidate> {
  return http<IdeaCandidate>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/candidates/${encodeURIComponent(candidateId)}`,
    {
      method: "PATCH",
      body: payload,
    }
  );
}

/** List idea clusters. */
export async function listIdeaClusters(
  projectId: string,
  params?: PaginationParams
): Promise<PaginatedResponse<IdeaCluster>> {
  return http<PaginatedResponse<IdeaCluster>>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/clusters`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Create an idea cluster. */
export async function createIdeaCluster(
  projectId: string,
  payload: Partial<IdeaCluster>
): Promise<IdeaCluster> {
  return http<IdeaCluster>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/clusters`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** List idea tickets. */
export async function listIdeaTickets(
  projectId: string,
  params?: PaginationParams & { status?: string }
): Promise<PaginatedResponse<IdeaTicket>> {
  return http<PaginatedResponse<IdeaTicket>>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/tickets`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Create an idea ticket. */
export async function createIdeaTicket(
  projectId: string,
  payload: Partial<IdeaTicket>
): Promise<IdeaTicket> {
  return http<IdeaTicket>(
    `/api/projects/${encodeURIComponent(projectId)}/ideas/tickets`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** List mission control tasks. */
export async function listMissionControlTasks(
  projectId: string,
  params?: PaginationParams & { column?: string; origin?: string }
): Promise<PaginatedResponse<MissionControlTask>> {
  return http<PaginatedResponse<MissionControlTask>>(
    `/api/projects/${encodeURIComponent(projectId)}/tasks`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Create a mission control task. */
export async function createMissionControlTask(
  projectId: string,
  payload: Partial<MissionControlTask>
): Promise<MissionControlTask> {
  return http<MissionControlTask>(
    `/api/projects/${encodeURIComponent(projectId)}/tasks`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Update a mission control task. */
export async function updateMissionControlTask(
  projectId: string,
  taskId: string,
  payload: Partial<MissionControlTask>
): Promise<MissionControlTask> {
  return http<MissionControlTask>(
    `/api/projects/${encodeURIComponent(projectId)}/tasks/${encodeURIComponent(taskId)}`,
    {
      method: "PATCH",
      body: payload,
    }
  );
}

/* ============================================================================
 * Knowledge graph / Knowledge Nexus
 * ==========================================================================*/

export interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  generatedAt: string;
}

/** Fetch the knowledge graph for a project. */
export async function fetchKnowledgeGraph(
  projectId: string,
  params?: { view?: string; focusNodeId?: string }
): Promise<KnowledgeGraph> {
  return http<KnowledgeGraph>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph`,
    {
      method: "GET",
      query: params,
    }
  );
}

/** Get a knowledge node. */
export async function getKnowledgeNode(
  projectId: string,
  nodeId: string
): Promise<KnowledgeNode> {
  return http<KnowledgeNode>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph/nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "GET",
    }
  );
}

/** Get neighbors for a knowledge node. */
export async function getKnowledgeNodeNeighbors(
  projectId: string,
  nodeId: string
): Promise<{ node: KnowledgeNode; neighbors: KnowledgeNode[]; edges: KnowledgeEdge[] }> {
  return http(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph/nodes/${encodeURIComponent(nodeId)}/neighbors`,
    {
      method: "GET",
    }
  );
}

/** Create a knowledge node. */
export async function createKnowledgeNode(
  projectId: string,
  payload: Partial<KnowledgeNode>
): Promise<KnowledgeNode> {
  return http<KnowledgeNode>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph/nodes`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Update a knowledge node. */
export async function updateKnowledgeNode(
  projectId: string,
  nodeId: string,
  payload: Partial<KnowledgeNode>
): Promise<KnowledgeNode> {
  return http<KnowledgeNode>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph/nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "PATCH",
      body: payload,
    }
  );
}

/** Create a knowledge edge. */
export async function createKnowledgeEdge(
  projectId: string,
  payload: Partial<KnowledgeEdge>
): Promise<KnowledgeEdge> {
  return http<KnowledgeEdge>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph/edges`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Delete a knowledge edge. */
export async function deleteKnowledgeEdge(
  projectId: string,
  edgeId: string
): Promise<void> {
  return http<void>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge-graph/edges/${encodeURIComponent(edgeId)}`,
    {
      method: "DELETE",
    }
  );
}

/** Search knowledge nodes. */
export async function searchKnowledge(
  projectId: string,
  query: string,
  params?: { type?: string; tags?: string[]; limit?: number; useVectorSearch?: boolean }
): Promise<KnowledgeNode[]> {
  return http<KnowledgeNode[]>(
    `/api/projects/${encodeURIComponent(projectId)}/knowledge/search`,
    {
      method: "POST",
      body: { query, ...params },
    }
  );
}

/* ============================================================================
 * Context / Working memory
 * ==========================================================================*/

/** Fetch the current context / working memory state. */
export async function getContext(projectId: string): Promise<ContextBudget> {
  return http<ContextBudget>(
    `/api/projects/${encodeURIComponent(projectId)}/context`,
    {
      method: "GET",
    }
  );
}

/** Add context items. */
export async function addContextItems(
  projectId: string,
  payload: { items: ContextItem[] }
): Promise<{ items: ContextItem[]; budget: ContextBudget }> {
  return http(
    `/api/projects/${encodeURIComponent(projectId)}/context/items`,
    {
      method: "POST",
      body: payload,
    }
  );
}

/** Update a context item. */
export async function updateContextItem(
  projectId: string,
  itemId: string,
  payload: Partial<ContextItem>
): Promise<ContextItem> {
  return http<ContextItem>(
    `/api/projects/${encodeURIComponent(projectId)}/context/items/${encodeURIComponent(itemId)}`,
    {
      method: "PATCH",
      body: payload,
    }
  );
}

/** Remove a context item. */
export async function removeContextItem(
  projectId: string,
  itemId: string
): Promise<ContextBudget> {
  return http<ContextBudget>(
    `/api/projects/${encodeURIComponent(projectId)}/context/items/${encodeURIComponent(itemId)}`,
    {
      method: "DELETE",
    }
  );
}

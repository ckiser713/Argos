// src/domain/api-types.ts
// Typed API contract for Argos, aligned with src/domain/types.ts.
// Pure TypeScript types/interfaces only — no runtime logic.

import type {
  ID,
  ArgosProject,
  ArgosProjectStatus,
  IngestSource,
  IngestSourceKind,
  IngestJob,
  IngestStage,
  IngestJobStatus,
  CanonicalDocument,
  CanonicalDocumentStatus,
  Chunk,
  Cluster,
  ClusterKind,
  KnowledgeNode,
  KnowledgeEdge,
  RoadmapNode,
  RoadmapNodeStatus,
  RoadmapPriority,
  RoadmapEdge,
  RoadmapEdgeKind,
  AgentRun,
  AgentRunStatus,
  AgentStep,
  AgentNodeState,
  AgentMessage,
  IdeaCandidate,
  IdeaType,
  IdeaStatus,
  IdeaCluster,
  IdeaTicket,
  IdeaTicketStatus,
  MissionControlTask,
  TaskColumnId,
  TaskOriginType,
  TaskPriority,
  TaskContextFile,
  ContextBudget,
  ContextItem,
  ContextItemType,
} from './types';

/* -------------------------------------------------------------------------- */
/* Generic Helpers */
/* -------------------------------------------------------------------------- */

export interface PaginatedResponse<T> {
  items: T[];
  nextCursor?: string | null;
  total?: number;
}

export interface SuccessResponse {
  success: boolean;
}

/* -------------------------------------------------------------------------- */
/* Projects */
/* -------------------------------------------------------------------------- */

export interface ListProjectsQuery {
  cursor?: string;
  limit?: number;
  status?: ArgosProjectStatus;
}

export type ListProjectsResponse = PaginatedResponse<ArgosProject>;

export interface CreateProjectRequest {
  name: string;
  slug?: string;
  description?: string;
}

export type CreateProjectResponse = ArgosProject;

export type GetProjectResponse = ArgosProject;

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  status?: ArgosProjectStatus;
  rootIdeaClusterId?: ID | null;
  roadmapId?: ID | null;
  defaultModelRoleId?: ID | null;
}

export type UpdateProjectResponse = ArgosProject;

export type DeleteProjectResponse = SuccessResponse;

/* -------------------------------------------------------------------------- */
/* Ingest Sources */
/* -------------------------------------------------------------------------- */

export interface ListIngestSourcesQuery {
  cursor?: string;
  limit?: number;
  kind?: IngestSourceKind;
}

export type ListIngestSourcesResponse = PaginatedResponse<IngestSource>;

export interface CreateIngestSourceRequest {
  kind: IngestSourceKind;
  name: string;
  description?: string;
  uri?: string;
}

export type CreateIngestSourceResponse = IngestSource;

export type GetIngestSourceResponse = IngestSource;

export type DeleteIngestSourceResponse = SuccessResponse;

/* -------------------------------------------------------------------------- */
/* Ingest Jobs */
/* -------------------------------------------------------------------------- */

export interface ListIngestJobsQuery {
  cursor?: string;
  limit?: number;
  status?: IngestJobStatus;
  stage?: IngestStage;
  sourceId?: ID;
}

export type ListIngestJobsResponse = PaginatedResponse<IngestJob>;

export interface CreateIngestJobItem {
  sourceId: ID;
  originalFilename: string;
  byteSize?: number;
  mimeType?: string;
  isDeepScan?: boolean;
}

export interface CreateIngestJobsRequest {
  jobs: CreateIngestJobItem[];
}

export interface CreateIngestJobsResponse {
  jobs: IngestJob[];
}

export type GetIngestJobResponse = IngestJob;

export type CancelIngestJobResponse = IngestJob;

/* -------------------------------------------------------------------------- */
/* Canonical Documents / Chunks / Clusters */
/* -------------------------------------------------------------------------- */

export interface ListCanonicalDocumentsQuery {
  cursor?: string;
  limit?: number;
  status?: CanonicalDocumentStatus;
  sourceId?: ID;
  ingestJobId?: ID;
  q?: string;
}

export type ListCanonicalDocumentsResponse = PaginatedResponse<CanonicalDocument>;

export type GetCanonicalDocumentResponse = CanonicalDocument;

export interface ListChunksQuery {
  cursor?: string;
  limit?: number;
}

export type ListChunksResponse = PaginatedResponse<Chunk>;

export interface ListClustersQuery {
  cursor?: string;
  limit?: number;
  kind?: ClusterKind;
}

export type ListClustersResponse = PaginatedResponse<Cluster>;

/* -------------------------------------------------------------------------- */
/* Knowledge Graph */
/* -------------------------------------------------------------------------- */

export type KnowledgeGraphView = 'default' | 'ideas' | 'tickets' | 'docs';

export interface GetKnowledgeGraphQuery {
  view?: KnowledgeGraphView;
  focusNodeId?: ID;
}

export interface GetKnowledgeGraphResponse {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  generatedAt: string;
}

export type GetKnowledgeGraphNodeResponse = KnowledgeNode;

export interface GetKnowledgeGraphNeighborsResponse {
  node: KnowledgeNode;
  neighbors: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

/* -------------------------------------------------------------------------- */
/* Roadmap / Dependencies */
/* -------------------------------------------------------------------------- */

export interface ListRoadmapNodesQuery {
  cursor?: string;
  limit?: number;
  status?: RoadmapNodeStatus;
  laneId?: ID;
}

export type ListRoadmapNodesResponse = PaginatedResponse<RoadmapNode>;

export interface CreateRoadmapNodeRequest {
  label: string;
  description?: string;
  status?: RoadmapNodeStatus;
  priority?: RoadmapPriority;
  startDate?: string;
  targetDate?: string;
  completedDate?: string;
  dependsOnIds?: ID[];
  laneId?: ID;
  ideaId?: ID;
  ticketId?: ID;
  missionControlTaskId?: ID;
}

export type CreateRoadmapNodeResponse = RoadmapNode;

export type GetRoadmapNodeResponse = RoadmapNode;

export type UpdateRoadmapNodeRequest = Partial<Omit<RoadmapNode, 'id' | 'projectId'>>;

export type UpdateRoadmapNodeResponse = RoadmapNode;

export interface ListRoadmapEdgesQuery {
  cursor?: string;
  limit?: number;
}

export type ListRoadmapEdgesResponse = PaginatedResponse<RoadmapEdge>;

export interface CreateRoadmapEdgeRequest {
  fromNodeId: ID;
  toNodeId: ID;
  kind?: RoadmapEdgeKind;
  label?: string;
}

export type CreateRoadmapEdgeResponse = RoadmapEdge;

export type DeleteRoadmapEdgeResponse = SuccessResponse;

/* -------------------------------------------------------------------------- */
/* Agent Runs / Steps / Node State / Messages (Deep Research) */
/* -------------------------------------------------------------------------- */

export interface ListAgentRunsQuery {
  cursor?: string;
  limit?: number;
  workflowId?: ID;
  status?: AgentRunStatus;
}

export type ListAgentRunsResponse = PaginatedResponse<AgentRun>;

export interface StartAgentRunRequest {
  workflowId: ID;
  inputQuery: string;
  contextItemIds?: ID[];
}

export type StartAgentRunResponse = AgentRun;

export type GetAgentRunResponse = AgentRun;

export interface ListAgentStepsQuery {
  cursor?: string;
  limit?: number;
}

export type ListAgentStepsResponse = PaginatedResponse<AgentStep>;

export interface ListAgentNodeStatesResponse {
  items: AgentNodeState[];
}

export interface ListAgentMessagesQuery {
  cursor?: string;
  limit?: number;
}

export type ListAgentMessagesResponse = PaginatedResponse<AgentMessage>;

export interface AppendAgentMessageRequest {
  content: string;
  contextItemIds?: ID[];
}

export type AppendAgentMessageResponse = AgentMessage;

export type CancelAgentRunResponse = AgentRun;

/* -------------------------------------------------------------------------- */
/* Ideas / Clusters / Tickets */
/* -------------------------------------------------------------------------- */

export interface ListIdeaCandidatesQuery {
  cursor?: string;
  limit?: number;
  status?: IdeaStatus;
  type?: IdeaType;
}

export type ListIdeaCandidatesResponse = PaginatedResponse<IdeaCandidate>;

export interface CreateIdeaCandidateRequest {
  type: IdeaType;
  summary: string;
  sourceLogIds?: ID[];
  sourceChannel?: 'chat' | 'email' | 'note' | 'file';
  sourceUser?: string;
  confidence?: number;
}

export type CreateIdeaCandidateResponse = IdeaCandidate;

export type UpdateIdeaCandidateRequest = Partial<Omit<IdeaCandidate, 'id' | 'projectId'>>;

export type UpdateIdeaCandidateResponse = IdeaCandidate;

export interface ListIdeaClustersQuery {
  cursor?: string;
  limit?: number;
}

export type ListIdeaClustersResponse = PaginatedResponse<IdeaCluster>;

export interface CreateIdeaClusterRequest {
  label: string;
  description?: string;
  color?: string;
  ideaIds?: ID[];
  priority?: RoadmapPriority;
}

export type CreateIdeaClusterResponse = IdeaCluster;

export type UpdateIdeaClusterRequest = Partial<Omit<IdeaCluster, 'id' | 'projectId'>>;

export type UpdateIdeaClusterResponse = IdeaCluster;

export interface ListTicketsQuery {
  cursor?: string;
  limit?: number;
  status?: IdeaTicketStatus;
}

export type ListTicketsResponse = PaginatedResponse<IdeaTicket>;

export interface CreateIdeaTicketRequest {
  ideaId: ID;
  title: string;
  originStory: string;
  category: IdeaTicket['category'];
  impliedTaskSummaries?: string[];
  repoHints?: string[];
  sourceQuotes?: string[];
}

export type CreateIdeaTicketResponse = IdeaTicket;

export type UpdateIdeaTicketRequest = Partial<Omit<IdeaTicket, 'id' | 'projectId'>>;

export type UpdateIdeaTicketResponse = IdeaTicket;

export interface ListMissionControlTasksQuery {
  cursor?: string;
  limit?: number;
  column?: TaskColumnId;
  origin?: TaskOriginType;
}

export type ListMissionControlTasksResponse = PaginatedResponse<MissionControlTask>;

export interface CreateMissionControlTaskRequest {
  title: string;
  origin: TaskOriginType;
  confidence?: number;
  column?: TaskColumnId;
  context?: TaskContextFile[];
  priority?: TaskPriority;
  ideaId?: ID;
  ticketId?: ID;
  roadmapNodeId?: ID;
}

export type CreateMissionControlTaskResponse = MissionControlTask;

export type UpdateMissionControlTaskRequest = Partial<Omit<MissionControlTask, 'id' | 'projectId'>>;

export type UpdateMissionControlTaskResponse = MissionControlTask;

/* -------------------------------------------------------------------------- */
/* Context Window */
/* -------------------------------------------------------------------------- */

export type GetContextResponse = ContextBudget;

export interface AddContextItemsRequest {
  items: {
    id?: ID;
    canonicalDocumentId?: ID;
    name: string;
    type: ContextItemType;
    tokens: number;
    pinned?: boolean;
  }[];
}

export interface AddContextItemsResponse {
  items: ContextItem[];
  budget: ContextBudget;
}

export interface UpdateContextItemRequest {
  pinned?: boolean;
}

export interface UpdateContextItemResponse {
  item: ContextItem;
  budget: ContextBudget;
}

export interface RemoveContextItemResponse {
  budget: ContextBudget;
}

/* -------------------------------------------------------------------------- */
/* Realtime Channels (WebSocket / SSE) */
/* -------------------------------------------------------------------------- */

export type IngestJobEvent =
  | { type: 'ingest.job.created'; job: IngestJob; }
  | { type: 'ingest.job.updated'; job: IngestJob; }
  | { type: 'ingest.job.completed'; job: IngestJob; }
  | { type: 'ingest.job.failed'; job: IngestJob; errorMessage?: string; };

export type AgentRunEvent =
  | { type: 'agent.run.created'; run: AgentRun; }
  | { type: 'agent.run.updated'; run: AgentRun; }
  | { type: 'agent.run.completed'; run: AgentRun; }
  | { type: 'agent.run.failed'; run: AgentRun; errorMessage?: string; }
  | { type: 'agent.step.updated'; step: AgentStep; }
  | { type: 'agent.message.appended'; message: AgentMessage; };

export type WorkflowNodeEvent =
  | { type: 'workflow.node_state.updated'; nodeState: AgentNodeState; };

export type ProjectActivityEventPayload = IngestJobEvent | AgentRunEvent | WorkflowNodeEvent;

export interface ProjectActivityEvent {
  eventId: string;
  createdAt: string;
  payload: ProjectActivityEventPayload;
}

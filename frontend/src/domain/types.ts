// src/domain/types.ts
// Central domain model definitions for the Cortex frontend.
// Pure TypeScript types/interfaces only — no runtime logic.

export type ID = string;

/**
 * High-level project container.
 * A CortexProject groups ingestion, canonical docs, ideas, tickets, and roadmaps.
 */
export type CortexProjectStatus = 'active' | 'archived' | 'draft';

export interface CortexProject {
  id: ID;
  slug: string;
  name: string;
  description?: string;
  status: CortexProjectStatus;
  createdAt: string;
  updatedAt: string;
  /**
   * Optional wiring to other entities that the UI frequently pivots around.
   */
  defaultModelRoleId?: ID;
  rootIdeaClusterId?: ID;
  roadmapId?: ID;
}

/* -------------------------------------------------------------------------- */
/* Ingestion / Sources */
/* -------------------------------------------------------------------------- */

export type IngestSourceKind =
  | 'file'
  | 'folder'
  | 'repo'
  | 'chat_export'
  | 'url'
  | 'manual_note';

export interface IngestSource {
  id: ID;
  projectId?: ID;
  kind: IngestSourceKind;
  /**
   * Human readable label shown in the Ingest Station cards (e.g. repo name, file name, chat title).
   */
  name: string;
  description?: string;
  /**
   * Where this source ultimately lives on disk or in a service.
   * Not necessarily exposed to the user, but useful for debug/tooltips.
   */
  uri?: string;
}

/**
 * Pipeline stage badges shown in Ingest Station.
 * These map directly onto the existing UI chips:
 * - QUEUED
 * - OCR_SCANNING
 * - MD_CONVERSION
 * - GRAPH_INDEXING
 * - COMPLETE
 */
export type IngestStage =
  | 'QUEUED'
  | 'OCR_SCANNING'
  | 'MD_CONVERSION'
  | 'GRAPH_INDEXING'
  | 'COMPLETE';

/**
 * Coarser status for an ingest job.
 * Used for filtering and overall state.
 */
export type IngestJobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

/**
 * An individual unit of work for ingestion (e.g., one file upload, one repo sync).
 * Drives the rows in the Ingest Station UI.
 */
export interface IngestJob {
  id: ID;
  projectId: ID;
  sourceId: ID;
  originalFilename: string;
  byteSize: number;
  mimeType?: string;
  isDeepScan: boolean;
  /**
   * Current processing stage (for UI badges).
   */
  stage: IngestStage;
  /**
   * Numeric progress for current stage (0-100).
   */
  progress: number;
  status: IngestJobStatus;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  errorMessage?: string;
  /**
   * If this ingest job resulted in a CanonicalDocument, link it.
   */
  canonicalDocumentId?: ID;
}

/* -------------------------------------------------------------------------- */
/* Canonical Documents, Chunks, Clusters */
/* -------------------------------------------------------------------------- */

export type CanonicalDocumentType =
  | 'pdf'
  | 'code'
  | 'markdown'
  | 'html'
  | 'text'
  | 'image'
  | 'chat';

export type CanonicalDocumentStatus =
  | 'pending'
  | 'canonicalizing'
  | 'indexed'
  | 'archived'
  | 'failed';

/**
 * The normalized, canonical representation of an ingested document.
 * These are the primary units for search, retrieval, and knowledge graph nodes.
 */
export interface CanonicalDocument {
  id: ID;
  projectId: ID;
  ingestJobId: ID;
  sourceId: ID;
  type: CanonicalDocumentType;
  name: string;
  title: string;
  description?: string;
  contentHash: string; // E.g., SHA256 of the processed text
  status: CanonicalDocumentStatus;
  tokenCount: number;
  chunkCount: number;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, any>; // Arbitrary metadata
}

/**
 * A smaller, semantically coherent segment of a CanonicalDocument.
 * Used for RAG and fine-grained highlighting.
 */
export interface Chunk {
  id: ID;
  canonicalDocumentId: ID;
  projectId: ID;
  index: number; // Order within the document
  text: string;
  embedding?: number[]; // Vector embedding
  tokenCount: number;
  metadata?: Record<string, any>;
  clusterId?: ID; // Link to a semantic cluster
}

export type ClusterKind = 'semantic' | 'topic' | 'roadmap_group' | 'idea_group';

/**
 * A grouping of related entities (chunks, ideas, etc.) based on semantic similarity or domain logic.
 * Used to drive Knowledge Nexus node sizes, colors, and higher-level analytics.
 */
export interface Cluster {
  id: ID;
  projectId: ID;
  kind: ClusterKind;
  name: string;
  description?: string;
  size: number; // Number of items in cluster (e.g., chunks)
  color?: string; // Hex code or named color for UI
  representativeChunkId?: ID; // A key chunk that represents the cluster
  metadata?: Record<string, any>;
}

/* -------------------------------------------------------------------------- */
/* Knowledge Graph */
/* -------------------------------------------------------------------------- */

export type KnowledgeNodeKind =
  | 'pdf' // deprecated, use canonical_doc
  | 'repo' // deprecated, use canonical_doc (for repo overview) or chunk_cluster
  | 'chat' // deprecated, use canonical_doc
  | 'canonical_doc'
  | 'chunk_cluster'
  | 'idea'
  | 'ticket'
  | 'project'
  | 'user'
  | 'workflow'
  | 'agent_run'
  | 'decision';

/**
 * A node in the force-directed knowledge graph (Knowledge Nexus).
 * Generalizes the existing `Node` in `KnowledgeNexus.tsx`.
 */
export interface KnowledgeNode {
  id: ID;
  projectId: ID;
  kind: KnowledgeNodeKind;
  label: string; // Display label
  size: number; // Visual size in force graph (e.g., for importance)
  color?: string; // Visual color
  description?: string;
  importance?: number; // Numeric importance score
  tags?: string[];
  /**
   * Optional links back to the underlying domain entities.
   */
  canonicalDocumentId?: ID;
  chunkClusterId?: ID;
  ideaId?: ID;
  ticketId?: ID;
  workflowId?: ID;
  agentRunId?: ID;
  decisionId?: ID;
}

export type KnowledgeEdgeKind =
  | 'semantic' // e.g., chunk A is related to chunk B
  | 'reference' // e.g., doc A references doc B
  | 'temporal' // e.g., event A happened before event B
  | 'hierarchy' // e.g., folder contains file
  | 'co_occurrence' // e.g., two terms often appear together
  | 'dependency' // for roadmap or workflow
  | 'mentions' // e.g., chat message mentions an idea
  | 'part_of' // e.g., chunk is part of document
  | 'generates' // e.g. agent run generates an idea
  | 'relates_to'; // general relationship

/**
 * An edge in the force-directed knowledge graph.
 * Generalizes the existing `Link` in `KnowledgeNexus.tsx`.
 */
export interface KnowledgeEdge {
  id: ID;
  projectId: ID;
  source: ID; // ID of the source KnowledgeNode
  target: ID; // ID of the target KnowledgeNode
  kind: KnowledgeEdgeKind;
  label?: string; // Optional label for the edge
  strength?: number; // Visual strength/thickness
  metadata?: Record<string, any>;
}

/* -------------------------------------------------------------------------- */
/* Roadmap / Dependencies */
/* -------------------------------------------------------------------------- */

export type RoadmapNodeStatus =
  | 'planned' // equivalent to DependencyTimeline 'pending'
  | 'in_progress'
  | 'blocked'
  | 'complete' // equivalent to DependencyTimeline 'completed'
  | 'dropped'; // explicitly cancelled/removed

export type RoadmapPriority = 'low' | 'medium' | 'high' | 'critical';

/**
 * A node on the project roadmap (e.g., a feature, an epic, a task).
 * Feeds the DependencyTimeline and other roadmap views.
 * Aligns with the 'Task' concept in DependencyTimeline.tsx.
 */
export interface RoadmapNode {
  id: ID;
  projectId: ID;
  label: string;
  description?: string;
  status: RoadmapNodeStatus;
  priority: RoadmapPriority;
  startDate?: string; // ISO-8601 date string
  targetDate?: string; // ISO-8601 date string
  completedDate?: string; // ISO-8601 date string
  laneId?: ID; // Corresponds to ClusterId in DependencyTimeline for grouping (e.g., NEXUS_CORE)
  dependsOnIds: ID[]; // IDs of other RoadmapNodes this one depends on
  /**
   * Back-links to originating entities.
   */
  ideaId?: ID;
  ticketId?: ID;
  missionControlTaskId?: ID;
}

export type RoadmapEdgeKind = 'dependency' | 'blocks' | 'relates_to';

/**
 * An edge representing a relationship between RoadmapNodes.
 */
export interface RoadmapEdge {
  id: ID;
  projectId: ID;
  source: ID; // ID of the source RoadmapNode
  target: ID; // ID of the target RoadmapNode
  kind: RoadmapEdgeKind;
  label?: string; // e.g., "requires", "blocks"
  metadata?: Record<string, any>;
}

/* -------------------------------------------------------------------------- */
/* Agent Runs, Steps, Node State, Messages (Deep Research) */
/* -------------------------------------------------------------------------- */

export type AgentRunStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

/**
 * Represents a single execution of an agent workflow (e.g., a Deep Research session).
 * Corresponds to a top-level run in DeepResearch.
 */
export interface AgentRun {
  id: ID;
  projectId: ID;
  workflowId: ID; // Which workflow definition was used
  inputQuery: string; // The initial query/prompt
  contextItemIds: ID[]; // IDs of context items active for this run
  status: AgentRunStatus;
  activeNodeId?: ID; // Current node being processed in the workflow
  iteration?: number; // Current iteration for iterative workflows
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  errorMessage?: string;
  messageIds: ID[]; // Ordered list of messages generated/exchanged during the run
  finalMessageId?: ID; // The ID of the final, conclusive message
  attachedDocumentIds: ID[]; // Documents identified/generated during the run
}

export type AgentStepStatus = 'pending' | 'processing' | 'complete' | 'failed';
export type AgentStepKind =
  | 'planner'
  | 'retrieval'
  | 'ranking'
  | 'tool'
  | 'generate'
  | 'branch'
  | 'merge'
  | 'final'
  | 'code_execution';

/**
 * An individual step executed by an agent within an AgentRun.
 * Corresponds to `LogStep` entries in DeepResearch.
 */
export interface AgentStep {
  id: ID;
  agentRunId: ID;
  projectId: ID;
  kind: AgentStepKind;
  label: string; // Short description of the step
  status: AgentStepStatus;
  detail?: string; // More detailed output/logs for the step
  startedAt: string;
  completedAt?: string;
  errorMessage?: string;
  /**
   * Link to the corresponding node in the workflow definition.
   */
  workflowNodeId?: ID;
  input?: Record<string, any>; // Opaque input to the step (for debug)
  output?: Record<string, any>; // Opaque output of the step (for debug)
}

export type AgentNodeStatus =
  | 'pending'
  | 'active'
  | 'complete'
  | 'failed'
  | 'skipped';

/**
 * The state of a specific node within an active AgentRun.
 * Used to drive `WorkflowConstruct` and `WorkflowVisualizer` node visuals.
 */
export interface AgentNodeState {
  workflowNodeId: ID; // ID of the node in the workflow definition
  agentRunId: ID;
  projectId: ID;
  status: AgentNodeStatus;
  iteration?: number; // If the node is part of an iterative loop
  lastActivityAt: string;
  metrics?: Record<string, number>; // e.g., { latency_ms, token_cost, calls }
  errorMessage?: string;
}

export type AgentMessageRole = 'user' | 'agent' | 'tool' | 'system';

/**
 * A message exchanged during an AgentRun.
 * Aligns with `Message` in DeepResearch.tsx.
 */
export interface AgentMessage {
  id: ID;
  agentRunId: ID;
  projectId: ID;
  role: AgentMessageRole;
  content: string;
  timestamp: string;
  /**
   * If the message is related to a specific document or parts of it.
   */
  relatedCanonicalDocumentId?: ID;
  highlightChunkIds?: ID[]; // IDs of chunks to highlight in the viewer
  /**
   * If the message was produced by specific agent steps.
   */
  stepIds?: ID[];
  metadata?: Record<string, any>;
}

/* -------------------------------------------------------------------------- */
/* Ideas, Clusters, Tickets, and Mission Control */
/* -------------------------------------------------------------------------- */

export type IdeaType =
  | 'infra'
  | 'feature'
  | 'project'
  | 'ops'
  | 'research_topic'
  | 'bug'
  | 'question';

export type IdeaStatus = 'pending' | 'clustered' | 'ticketed' | 'discarded';

/**
 * A raw idea candidate extracted from various sources (chat, docs, etc.).
 * Aligns with `Idea` in StrategyDeck.tsx.
 */
export interface IdeaCandidate {
  id: ID;
  projectId: ID;
  type: IdeaType;
  summary: string;
  status: IdeaStatus;
  sourceLogIds?: ID[]; // Links to ChatLog/ConversationLog entries
  sourceChannel?: string; // e.g., "slack_dev", "email_thread_123"
  sourceUser?: string;
  confidence: number; // 0.0 - 1.0, how confident we are in this as an idea
  createdAt: string;
  updatedAt: string;
  clusterId?: ID; // After clustering
  ticketId?: ID; // After being converted to a ticket
}

/**
 * A grouping of related IdeaCandidates.
 * Used by StrategyDeck.
 */
export interface IdeaCluster {
  id: ID;
  projectId: ID;
  name: string;
  description?: string;
  ideaIds: ID[]; // IDs of contained ideas
  color?: string; // For UI visualization in StrategyDeck
  priority?: RoadmapPriority; // Inherited or assigned priority
  createdAt: string;
  updatedAt: string;
}

export type IdeaTicketStatus =
  | 'draft'
  | 'groomed'
  | 'ready_for_dev'
  | 'in_progress'
  | 'done'
  | 'rejected';

/**
 * A structured ticket derived from an IdeaCandidate.
 * Aligns with `StructuredTicket` in PmDissection.tsx.
 */
export interface IdeaTicket {
  id: ID;
  projectId: ID;
  ideaId: ID; // Link back to original idea
  title: string;
  originStory: string; // Context/quotes from where the idea came
  category:
    | 'new_project'
    | 'feature_for_existing_repo'
    | 'infrastructure'
    | 'research_topic'
    | 'operational_task';
  impliedTaskSummaries?: string[]; // Short summaries of tasks needed
  repoHints?: string[]; // Potential repositories involved
  sourceQuotes?: string[]; // Direct quotes supporting the ticket
  status: IdeaTicketStatus;
  priority?: RoadmapPriority;
  createdAt: string;
  updatedAt: string;
  roadmapNodeId?: ID; // Once added to the roadmap
  missionControlTaskId?: ID; // Once added to mission control
}

export type TaskColumnId =
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'done'
  | 'blocked';

export type TaskOriginType = 'chat' | 'pdf' | 'repo' | 'system' | 'manual';

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

/**
 * A file or document associated with a MissionControlTask.
 * Aligns with `ContextFile` in MissionControlBoard.tsx.
 */
export interface TaskContextFile {
  name: string;
  type: 'code' | 'doc' | 'chat' | 'url';
  uri?: string; // Optional URI for direct linking
}

/**
 * A task on the Mission Control Board.
 * Aligns with `Task` in MissionControlBoard.tsx.
 */
export interface MissionControlTask {
  id: ID;
  projectId: ID;
  title: string;
  origin: TaskOriginType;
  confidence?: number; // 0.0 - 1.0, how confident AI is in this task
  column: TaskColumnId;
  context: TaskContextFile[];
  priority: TaskPriority;
  createdAt: string;
  updatedAt: string;
  ideaId?: ID; // Link back to originating idea
  ticketId?: ID; // Link back to originating ticket
  roadmapNodeId?: ID; // Link to roadmap item if applicable
}

/* -------------------------------------------------------------------------- */
/* Context Window / Deep Research Context */
/* -------------------------------------------------------------------------- */

export type ContextItemType =
  | 'pdf' // deprecated, use canonical_doc
  | 'repo' // deprecated, use canonical_doc (for repo overview)
  | 'chat' // deprecated, use canonical_doc (for chat export)
  | 'code' // deprecated, use canonical_doc
  | 'web'
  | 'canonical_doc'
  | 'chunk_selection' // specific text selection from a doc
  | 'search_result'; // snippet from a search result

/**
 * An item currently loaded into the model's context window.
 * Aligns with `ContextItem` in ContextPrism.tsx.
 */
export interface ContextItem {
  id: ID;
  projectId: ID;
  name: string; // Display name
  type: ContextItemType;
  tokens: number; // Number of tokens this item consumes
  canonicalDocumentId?: ID; // Link to source document if applicable
  pinned: boolean; // If the user has manually pinned this item
  lastUsedAt: string; // For LRU eviction policies
  metadata?: Record<string, any>;
}

/**
 * Represents the current state and capacity of the model's context window.
 * Feeds the context donut meter and capacity indicators.
 */
export interface ContextBudget {
  projectId: ID;
  maxTokens: number;
  usedTokens: number;
  availableTokens: number;
  reservedTokens?: number; // e.g., for system prompts
  items: ContextItem[];
}

Cortex API Contract
High-level, implementation-agnostic contract for the Cortex backend. All responses are JSON over HTTP. Realtime updates are delivered via WebSocket or Server-Sent Events (SSE) using JSON payloads.

Domain entities referenced below come from src/domain/types.ts.

0. Conventions
   Base URL: `/api` (all paths below are relative to this).

   Auth: Token-based (e.g. `Authorization: Bearer <token>`). Not further specified here.

   Dates: ISO-8601 strings in UTC.

   IDs: All `id` and `*Id` fields are string IDs.

   Pagination:
   Queries that return lists accept optional `cursor` and `limit` query params.
   Responses use a common envelope:
   `PaginatedResponse<T> = { items: T[]; nextCursor?: string | null; total?: number }`.

1. Projects
   1.1 List projects
       `GET /projects`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `status?: CortexProjectStatus`
       Response: `PaginatedResponse<CortexProject>`

   1.2 Create project
       `POST /projects`
       Request body:
         `{ name: string; slug?: string; description?: string; }`
       Response: `CortexProject`

   1.3 Get project
       `GET /projects/{projectId}`
       Response: `CortexProject`

   1.4 Update project
       `PATCH /projects/{projectId}`
       Request body (all optional):
         `{ name?: string; description?: string; status?: CortexProjectStatus; rootIdeaClusterId?: ID | null; roadmapId?: ID | null; defaultModelRoleId?: ID | null; }`
       Response: `CortexProject`

   1.5 Delete/Archive project
       `DELETE /projects/{projectId}`
       Response: `{ success: boolean }`

2. Ingest & Sources
   2.1 List ingest sources
       `GET /projects/{projectId}/ingest/sources`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `kind?: IngestSourceKind`
       Response: `PaginatedResponse<IngestSource>`

   2.2 Create ingest source
       `POST /projects/{projectId}/ingest/sources`
       Request body:
         `{ kind: IngestSourceKind; name: string; description?: string; uri?: string; }`
       Response: `IngestSource`

   2.3 Get single ingest source
       `GET /projects/{projectId}/ingest/sources/{sourceId}`
       Response: `IngestSource`

   2.4 Delete ingest source
       `DELETE /projects/{projectId}/ingest/sources/{sourceId}`
       Response: `{ success: boolean }`

   2.5 List ingest jobs
       Supports the Ingest Station table, stage/status filters, and progress bars.
       `GET /projects/{projectId}/ingest/jobs`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `status?: IngestJobStatus`
         - `stage?: IngestStage`
         - `sourceId?: ID`
       Response: `PaginatedResponse<IngestJob>`

   2.6 Create ingest job(s)
       Typically called after files are uploaded or a repo/chat source is registered.
       `POST /projects/{projectId}/ingest/jobs`
       Request body:
         `{ jobs: { sourceId: ID; originalFilename: string; byteSize?: number; mimeType?: string; isDeepScan?: boolean; }[] }`
       Response: `{ jobs: IngestJob[] }`

   2.7 Get ingest job
       `GET /projects/{projectId}/ingest/jobs/{jobId}`
       Response: `IngestJob`

   2.8 Cancel ingest job
       `POST /projects/{projectId}/ingest/jobs/{jobId}/cancel`
       Response: `IngestJob` (with status typically cancelled)

3. Canonical Documents, Chunks, Clusters
   3.1 List canonical documents
       Feeds Doc Atlas-style tables and Deep Research side panels.
       `GET /projects/{projectId}/canonical-documents`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `status?: CanonicalDocumentStatus`
         - `sourceId?: ID`
         - `ingestJobId?: ID`
         - `q?: string` (full-text search over title/metadata)
       Response: `PaginatedResponse<CanonicalDocument>`

   3.2 Get canonical document
       `GET /projects/{projectId}/canonical-documents/{canonicalDocumentId}`
       Response: `CanonicalDocument`

   3.3 List chunks for a document
       Used for Deep Research highlighting and debug views.
       `GET /projects/{projectId}/canonical-documents/{canonicalDocumentId}/chunks`
       Query params:
         - `cursor?: string`
         - `limit?: number`
       Response: `PaginatedResponse<Chunk>`

   3.4 List clusters
       Topic/semantic clusters backing Knowledge Nexus and idea clustering.
       `GET /projects/{projectId}/clusters`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `kind?: ClusterKind`
       Response: `PaginatedResponse<Cluster>`

4. Knowledge Graph
   4.1 Get knowledge graph snapshot
       Used to render the Knowledge Nexus force-directed graph.
       `GET /projects/{projectId}/knowledge-graph`
       Query params:
         - `view?: 'default' | 'ideas' | 'tickets' | 'docs'` (optional preset)
         - `focusNodeId?: ID` (optional focus)
       Response:
         `{ nodes: KnowledgeNode[]; edges: KnowledgeEdge[]; generatedAt: string; }`

   4.2 Get node details
       `GET /projects/{projectId}/knowledge-graph/nodes/{nodeId}`
       Response: `KnowledgeNode`

   4.3 Get neighbors for a node
       `GET /projects/{projectId}/knowledge-graph/nodes/{nodeId}/neighbors`
       Response:
         `{ node: KnowledgeNode; neighbors: KnowledgeNode[]; edges: KnowledgeEdge[]; }`

5. Roadmap & Dependencies
   5.1 List roadmap nodes
       Feeds DependencyTimeline and any roadmap list views.
       `GET /projects/{projectId}/roadmap/nodes`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `status?: RoadmapNodeStatus`
         - `laneId?: ID`
       Response: `PaginatedResponse<RoadmapNode>`

   5.2 Create roadmap node
       `POST /projects/{projectId}/roadmap/nodes`
       Request body:
         `{ label: string; description?: string; status?: RoadmapNodeStatus; priority?: RoadmapPriority; startDate?: string; targetDate?: string; dependsOnIds?: ID[]; laneId?: ID; ideaId?: ID; ticketId?: ID; missionControlTaskId?: ID; }`
       Response: `RoadmapNode`

   5.3 Get roadmap node
       `GET /projects/{projectId}/roadmap/nodes/{nodeId}`
       Response: `RoadmapNode`

   5.4 Update roadmap node
       `PATCH /projects/{projectId}/roadmap/nodes/{nodeId}`
       Request body: any subset of `RoadmapNode` fields except `id` & `projectId`.
       Response: `RoadmapNode`

   5.5 List roadmap edges
       `GET /projects/{projectId}/roadmap/edges`
       Query params:
         - `cursor?: string`
         - `limit?: number`
       Response: `PaginatedResponse<RoadmapEdge>`

   5.6 Create roadmap edge
       `POST /projects/{projectId}/roadmap/edges`
       Request body:
         `{ fromNodeId: ID; toNodeId: ID; kind?: RoadmapEdgeKind; label?: string; }`
       Response: `RoadmapEdge`

   5.7 Delete roadmap edge
       `DELETE /projects/{projectId}/roadmap/edges/{edgeId}`
       Response: `{ success: boolean }`

6. Agent Runs, Steps, Node State, Messages (Deep Research)
   6.1 List agent runs
       `GET /projects/{projectId}/agent-runs`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `workflowId?: ID`
         - `status?: AgentRunStatus`
       Response: `PaginatedResponse<AgentRun>`

   6.2 Start a new agent run
       Used by Deep Research when the user submits a new query.
       `POST /projects/{projectId}/agent-runs`
       Request body:
         `{ workflowId: ID; inputQuery: string; contextItemIds?: ID[]; }`
       Response: `AgentRun`

   6.3 Get agent run
       `GET /projects/{projectId}/agent-runs/{runId}`
       Response: `AgentRun`

   6.4 List steps for a run
       `GET /projects/{projectId}/agent-runs/{runId}/steps`
       Query params:
         - `cursor?: string`
         - `limit?: number`
       Response: `PaginatedResponse<AgentStep>`

   6.5 List node state for a run
       Used by WorkflowConstruct / WorkflowVisualizer for node coloring and tooltips.
       `GET /projects/{projectId}/agent-runs/{runId}/node-states`
       Response: `{ items: AgentNodeState[] }`

   6.6 List messages for a run (Deep Research stream)
       `GET /projects/{projectId}/agent-runs/{runId}/messages`
       Query params:
         - `cursor?: string`
         - `limit?: number`
       Response: `PaginatedResponse<AgentMessage>`

   6.7 Append user message to an existing run
       Supports follow-up questions in Deep Research.
       `POST /projects/{projectId}/agent-runs/{runId}/messages`
       Request body:
         `{ content: string; contextItemIds?: ID[]; }`
       Response: `AgentMessage` (the created user message)

   6.8 Cancel a run
       `POST /projects/{projectId}/agent-runs/{runId}/cancel`
       Response: `AgentRun` (with status cancelled)

7. Ideas, Clusters, Tickets, Mission Control Tasks
   7.1 List idea candidates
       `GET /projects/{projectId}/ideas/candidates`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `status?: IdeaStatus`
         - `type?: IdeaType`
       Response: `PaginatedResponse<IdeaCandidate>`

   7.2 Create idea candidate
       Typically from log ingestion or manual capture.
       `POST /projects/{projectId}/ideas/candidates`
       Request body:
         `{ type: IdeaType; summary: string; sourceLogIds?: ID[]; sourceChannel?: 'chat' | 'email' | 'note' | 'file'; sourceUser?: string; confidence?: number; }`
       Response: `IdeaCandidate`

   7.3 Update idea candidate
       `PATCH /projects/{projectId}/ideas/candidates/{ideaId}`
       Request body: subset of `IdeaCandidate` writable fields (excluding ids and projectId).
       Response: `IdeaCandidate`

   7.4 List idea clusters
       `GET /projects/{projectId}/ideas/clusters`
       Query params:
         - `cursor?: string`
         - `limit?: number`
       Response: `PaginatedResponse<IdeaCluster>`

   7.5 Create idea cluster
       `POST /projects/{projectId}/ideas/clusters`
       Request body:
         `{ label: string; description?: string; color?: string; ideaIds?: ID[]; priority?: RoadmapPriority; }`
       Response: `IdeaCluster`

   7.6 Update idea cluster
       `PATCH /projects/{projectId}/ideas/clusters/{clusterId}`
       Request body: subset of `IdeaCluster` writable fields.
       Response: `IdeaCluster`

   7.7 List tickets
       `GET /projects/{projectId}/ideas/tickets`
       Query params:
         - `cursor?: string`
         - `limit?: number`
         - `status?: IdeaTicketStatus`
       Response: `PaginatedResponse<IdeaTicket>`

   7.8 Create ticket from idea
       `POST /projects/{projectId}/ideas/tickets`
       Request body:
         `{ ideaId: ID; title: string; originStory: string; category: IdeaTicket['category']; impliedTaskSummaries?: string[]; repoHints?: string[]; sourceQuotes?: string; }`
       Response: `IdeaTicket`

   7.9 Update ticket
       `PATCH /projects/{projectId}/ideas/tickets/{ticketId}`
       Request body: subset of `IdeaTicket` writable fields.
       Response: `IdeaTicket`

   7.10 List Mission Control tasks
        Powers MissionControlBoard columns.
        `GET /projects/{projectId}/tasks`
        Query params:
          - `cursor?: string`
          - `limit?: number`
          - `column?: TaskColumnId`
          - `origin?: TaskOriginType`
        Response: `PaginatedResponse<MissionControlTask>`

   7.11 Create Mission Control task
        `POST /projects/{projectId}/tasks`
        Request body:
          `{ title: string; origin: TaskOriginType; confidence?: number; column?: TaskColumnId; context?: TaskContextFile[]; priority?: TaskPriority; ideaId?: ID; ticketId?: ID; roadmapNodeId?: ID; }`
        Response: `MissionControlTask`

   7.12 Update Mission Control task (drag/drop, edits)
        `PATCH /projects/{projectId}/tasks/{taskId}`
        Request body: subset of `MissionControlTask` writable fields (e.g. column, priority).
        Response: `MissionControlTask`

8. Context Window
   8.1 Get context budget and items
       Feeds ContextPrism and any context donut meters.
       `GET /projects/{projectId}/context`
       Response: `ContextBudget`

   8.2 Add context items
       Add one or more items to the current context window.
       `POST /projects/{projectId}/context/items`
       Request body:
         `{ items: { canonicalDocumentId?: ID; name: string; type: ContextItemType; tokens: number; pinned?: boolean; }[] }`
       Response: `{ items: ContextItem[]; budget: ContextBudget; }`

   8.3 Update context item
       `PATCH /projects/{projectId}/context/items/{contextItemId}`
       Request body:
         `{ pinned?: boolean; }`
       Response: `{ item: ContextItem; budget: ContextBudget; }`

   8.4 Remove context item
       `DELETE /projects/{projectId}/context/items/{contextItemId}`
       Response: `{ budget: ContextBudget; }`

9. Realtime Channels (WebSocket / SSE)
   The backend SHOULD support either WebSocket or SSE; the contract for payloads is the same. Below we assume WebSocket paths; SSE could use GET on analogous `/events/...` endpoints.

   9.1 Ingest job events
       `WebSocket ws/projects/{projectId}/ingest`
       Events are sent as JSON frames of type `IngestJobEvent`.
       `IngestJobEvent = | { type: 'ingest.job.created'; job: IngestJob; } | { type: 'ingest.job.updated'; job: IngestJob; } | { type: 'ingest.job.completed'; job: IngestJob; } | { type: 'ingest.job.failed'; job: IngestJob; errorMessage?: string; }`
       This supports:
         - Live progress bar updates in Ingest Station.
         - Stage/status badge changes without polling.

   9.2 Agent run + Deep Research events
       `WebSocket ws/projects/{projectId}/agent-runs/{runId}`
       Events are sent as JSON frames that are the union of `AgentRunEvent` and `WorkflowNodeEvent`.
       `AgentRunEvent = | { type: 'agent.run.created'; run: AgentRun; } | { type: 'agent.run.updated'; run: AgentRun; } | { type: 'agent.run.completed'; run: AgentRun; } | { type: 'agent.run.failed'; run: AgentRun; errorMessage?: string; } | { type: 'agent.step.updated'; step: AgentStep; } | { type: 'agent.message.appended'; message: AgentMessage; }`
       `WorkflowNodeEvent = | { type: 'workflow.node_state.updated'; nodeState: AgentNodeState; }`
       These events power:
         - Deep Research message stream (`agent.message.appended`).
         - Agent step list progression (`agent.step.updated`).
         - Workflow visualization node state (`workflow.node_state.updated`).
         - Run-level status pills and completion UI (`agent.run.updated / agent.run.completed`).

   9.3 Optional: Project-level activity stream
       `WebSocket ws/projects/{projectId}/events`
       A future aggregate stream that can multiplex:
         - `IngestJobEvent`
         - `AgentRunEvent`
         - `WorkflowNodeEvent`
         - (Optionally) idea/task/roadmap changes
       Each frame would be an envelope like:
       `{ eventId: string; createdAt: string; payload: IngestJobEvent | AgentRunEvent | WorkflowNodeEvent; }`
       This is optional for v1 but gives a single subscription point if desired by the frontend.

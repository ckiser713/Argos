from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.common import to_camel

from pydantic import BaseModel, ConfigDict, Field

# -------- Core / System --------


# -------- Context / Memory --------


class ContextItemType(str, Enum):
    PDF = "pdf"
    REPO = "repo"
    CHAT = "chat"
    OTHER = "other"

    @classmethod
    def _missing_(cls, value: object) -> 'ContextItemType':
        if isinstance(value, str):
            normalized = value.lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return super()._missing_(value)


class ContextItem(BaseModel):
    id: str
    name: str
    type: ContextItemType
    tokens: int = Field(ge=0)
    pinned: bool = False
    canonical_document_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ContextBudget(BaseModel):
    project_id: str
    total_tokens: int
    used_tokens: int
    available_tokens: int
    items: List[ContextItem] = Field(default_factory=list)

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ContextItemCreate(BaseModel):
    id: Optional[str] = None
    name: str
    type: ContextItemType
    tokens: int = Field(ge=0)
    pinned: bool = False
    canonical_document_id: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AddContextItemsRequest(BaseModel):
    items: List[ContextItemCreate]


class AddContextItemsResponse(BaseModel):
    items: List[ContextItem]
    budget: ContextBudget

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RemoveContextItemResponse(BaseModel):
    budget: ContextBudget

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# -------- Workflows / Graphs --------


class WorkflowNode(BaseModel):
    id: str
    label: str
    x: float
    y: float
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str


class WorkflowGraph(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowRun(BaseModel):
    id: str
    project_id: str
    workflow_id: str
    status: WorkflowRunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    last_message: Optional[str] = None
    task_id: Optional[str] = None
    paused_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class WorkflowNodeStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowNodeState(BaseModel):
    node_id: str
    status: WorkflowNodeStatus
    progress: float = Field(ge=0.0, le=1.0)
    messages: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# -------- Ingestion --------


class IngestStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestJob(BaseModel):
    id: str
    project_id: Optional[str] = None
    source_path: str
    original_filename: Optional[str] = None
    byte_size: Optional[int] = None
    mime_type: Optional[str] = None
    stage: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    status: IngestStatus
    progress: float = Field(ge=0.0, le=1.0)
    message: Optional[str] = None
    error_message: Optional[str] = None
    canonical_document_id: Optional[str] = None


class IngestRequest(BaseModel):
    source_path: str = Field(description="Path or URI to ingest (local file, directory, etc.)")


# -------- Agents --------


class AgentProfile(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PENDING_INPUT = "pending_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(BaseModel):
    id: str
    project_id: str
    workflow_id: Optional[str] = None
    agent_id: str
    status: AgentRunStatus
    input_query: Optional[str] = None
    input_prompt: Optional[str] = None
    output_summary: Optional[str] = None
    context_item_ids: List[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: Optional[datetime] = None


class AgentRunRequest(BaseModel):
    project_id: Optional[str] = None
    agent_id: str
    input_prompt: str
    context_item_ids: List[str] = Field(default_factory=list)


class AgentStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStep(BaseModel):
    id: str
    run_id: str
    step_number: int
    node_id: Optional[str] = None
    status: AgentStepStatus
    input: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class AgentMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentMessage(BaseModel):
    id: str
    run_id: str
    role: AgentMessageRole
    content: str
    context_item_ids: List[str] = Field(default_factory=list)
    created_at: datetime


class AgentNodeState(BaseModel):
    run_id: str
    node_id: str
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    messages: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AppendMessageRequest(BaseModel):
    content: str
    context_item_ids: List[str] = Field(default_factory=list)


# -------- Ideas / Project Tickets --------


class IdeaCandidateStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class IdeaCandidate(BaseModel):
    id: str
    project_id: str
    type: str
    title: str
    summary: str
    status: IdeaCandidateStatus
    confidence: float = Field(ge=0.0, le=1.0)
    source_log_ids: List[str] = Field(default_factory=list)
    source_channel: Optional[str] = None
    source_user: Optional[str] = None
    created_at: datetime


class IdeaCluster(BaseModel):
    id: str
    project_id: str
    label: str
    description: Optional[str] = None
    color: Optional[str] = None
    idea_ids: List[str] = Field(default_factory=list)
    priority: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IdeaTicketStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class IdeaTicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IdeaTicket(BaseModel):
    id: str
    project_id: str
    idea_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: IdeaTicketStatus
    priority: IdeaTicketPriority
    origin_story: Optional[str] = None
    category: Optional[str] = None
    implied_task_summaries: List[str] = Field(default_factory=list)
    repo_hints: List[str] = Field(default_factory=list)
    source_quotes: Optional[str] = None
    source_channel: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime


class MissionControlTaskColumn(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class MissionControlTaskOrigin(str, Enum):
    REPO = "repo"
    CHAT = "chat"
    PDF = "pdf"
    MANUAL = "manual"


class MissionControlTask(BaseModel):
    id: str
    project_id: str
    title: str
    origin: MissionControlTaskOrigin
    confidence: float = Field(ge=0.0, le=1.0)
    column: MissionControlTaskColumn
    context: List[ContextItem] = Field(default_factory=list)
    priority: Optional[str] = None
    idea_id: Optional[str] = None
    ticket_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# -------- Roadmap --------


class RoadmapNodeStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class RoadmapNodePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RoadmapNodeType(str, Enum):
    TASK = "task"
    DECISION = "decision"
    MILESTONE = "milestone"


class RoadmapNode(BaseModel):
    id: str
    project_id: str
    label: str
    status: RoadmapNodeStatus = Field(default=RoadmapNodeStatus.PENDING)
    node_type: RoadmapNodeType = Field(default=RoadmapNodeType.TASK)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    depends_on_ids: List[str] = Field(default_factory=list)
    lane_id: Optional[str] = None
    idea_id: Optional[str] = None
    ticket_id: Optional[str] = None
    mission_control_task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class RoadmapEdgeKind(str, Enum):
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"


class RoadmapEdge(BaseModel):
    id: str
    project_id: str
    from_node_id: str
    to_node_id: str
    kind: RoadmapEdgeKind
    label: Optional[str] = None
    created_at: datetime


class RoadmapGraph(BaseModel):
    nodes: List[RoadmapNode]
    edges: List[RoadmapEdge]
    generated_at: datetime


# -------- Knowledge Graph --------


class KnowledgeNode(BaseModel):
    id: str
    project_id: str
    title: str
    summary: Optional[str] = None
    text: Optional[str] = None
    type: str
    tags: List[str] = Field(default_factory=list)
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeEdge(BaseModel):
    id: str
    project_id: str
    source: str
    target: str
    type: str
    weight: Optional[float] = None
    label: Optional[str] = None
    created_at: Optional[datetime] = None


class KnowledgeGraph(BaseModel):
    nodes: List[KnowledgeNode]
    edges: List[KnowledgeEdge]
    generated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=100)
    max_results: int = Field(default=10, ge=1, le=100)  # Alias for limit
    use_vector_search: bool = Field(default=True, alias="useVectorSearch")

    def __init__(self, **data):
        # Support both limit and max_results
        if "limit" in data and "max_results" not in data:
            data["max_results"] = data["limit"]
        elif "max_results" in data and "limit" not in data:
            data["limit"] = data["max_results"]
        super().__init__(**data)


# -------- Simple text response for stubs --------


class MessageResponse(BaseModel):
    message: str


# -------- Streaming Events --------


class IngestJobEventType(str, Enum):
    QUEUED = "ingest.job.queued"
    RUNNING = "ingest.job.running"
    COMPLETED = "ingest.job.completed"
    FAILED = "ingest.job.failed"


class IngestJobEvent(BaseModel):
    event_type: IngestJobEventType
    job: IngestJob


class AgentRunEventType(str, Enum):
    PENDING = "agent.run.pending"
    RUNNING = "agent.run.running"
    COMPLETED = "agent.run.completed"
    FAILED = "agent.run.failed"


class AgentRunEvent(BaseModel):
    event_type: AgentRunEventType
    run: AgentRun


class WorkflowNodeEventType(str, Enum):
    NODE_STARTED = "workflow.node.started"
    NODE_PROGRESS = "workflow.node.progress"
    NODE_COMPLETED = "workflow.node.completed"
    NODE_FAILED = "workflow.node.failed"


class WorkflowNodeEvent(BaseModel):
    event_type: WorkflowNodeEventType
    run_id: str
    node_id: str
    state: WorkflowNodeState

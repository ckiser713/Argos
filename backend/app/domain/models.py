from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


# -------- Core / System --------




# -------- Context / Memory --------

class ContextItemType(str, Enum):
    PDF = "pdf"
    REPO = "repo"
    CHAT = "chat"
    OTHER = "other"


class ContextItem(BaseModel):
    id: str
    name: str
    type: ContextItemType
    tokens: int = Field(ge=0)


# -------- Workflows / Graphs --------

class WorkflowNode(BaseModel):
    id: str
    label: str
    x: float
    y: float


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str


class WorkflowGraph(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]


class WorkflowRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    status: WorkflowRunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    last_message: Optional[str] = None


class WorkflowNodeStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowNodeState(BaseModel):
    node_id: str
    status: WorkflowNodeStatus
    progress: float = Field(ge=0.0, le=1.0)


# -------- Ingestion --------

class IngestStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestJob(BaseModel):
    id: str
    source_path: str
    created_at: datetime
    status: IngestStatus
    progress: float = Field(ge=0.0, le=1.0)
    message: Optional[str] = None


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
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(BaseModel):
    id: str
    agent_id: str
    status: AgentRunStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_prompt: str
    output_summary: Optional[str] = None


class AgentRunRequest(BaseModel):
    agent_id: str
    input_prompt: str


# -------- Ideas / Project Tickets --------




# -------- Knowledge Graph --------

class KnowledgeNode(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    related_ids: List[str] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    query: str
    max_results: int = Field(default=10, ge=1, le=100)


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

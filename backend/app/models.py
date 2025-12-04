"""
SQLAlchemy ORM Models for Cortex Backend.

These models mirror the existing SQLite schema from db.py,
providing full ORM support for both SQLite and PostgreSQL.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class Project(Base):
    """Project model - core entity for organizing work."""
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    slug = Column(String(255), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    default_model_role_id = Column(String(36), nullable=True)
    root_idea_cluster_id = Column(String(36), nullable=True)
    roadmap_id = Column(String(36), nullable=True)
    
    # Relationships
    ingest_sources = relationship("IngestSource", back_populates="project", cascade="all, delete-orphan")
    ingest_jobs = relationship("IngestJob", back_populates="project", cascade="all, delete-orphan")
    idea_tickets = relationship("IdeaTicket", back_populates="project", cascade="all, delete-orphan")
    knowledge_nodes = relationship("KnowledgeNode", back_populates="project", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="project", cascade="all, delete-orphan")
    idea_candidates = relationship("IdeaCandidate", back_populates="project", cascade="all, delete-orphan")
    idea_clusters = relationship("IdeaCluster", back_populates="project", cascade="all, delete-orphan")
    roadmaps = relationship("Roadmap", back_populates="project", cascade="all, delete-orphan")
    context_items = relationship("ContextItem", back_populates="project", cascade="all, delete-orphan")
    workflow_graphs = relationship("WorkflowGraph", back_populates="project", cascade="all, delete-orphan")
    workflow_runs = relationship("WorkflowRun", back_populates="project", cascade="all, delete-orphan")
    roadmap_nodes = relationship("RoadmapNode", back_populates="project", cascade="all, delete-orphan")
    roadmap_edges = relationship("RoadmapEdge", back_populates="project", cascade="all, delete-orphan")
    knowledge_edges = relationship("KnowledgeEdge", back_populates="project", cascade="all, delete-orphan")
    gap_reports = relationship("GapReport", back_populates="project", cascade="all, delete-orphan")
    chat_segments = relationship("ChatSegment", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_projects_status", "status"),
        Index("idx_projects_slug", "slug"),
    )


class IngestSource(Base):
    """Ingest source - data sources for document ingestion."""
    __tablename__ = "ingest_sources"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    kind = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    uri = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="ingest_sources")
    ingest_jobs = relationship("IngestJob", back_populates="source", cascade="all, delete-orphan")
    idea_candidates = relationship("IdeaCandidate", back_populates="source", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_ingest_sources_project", "project_id"),
    )


class IngestJob(Base):
    """Ingest job - tracks document processing jobs."""
    __tablename__ = "ingest_jobs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    source_path = Column(Text, nullable=True)
    source_id = Column(String(36), ForeignKey("ingest_sources.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    byte_size = Column(Integer, nullable=False, default=0)
    mime_type = Column(String(100), nullable=True)
    is_deep_scan = Column(Integer, nullable=False, default=0)
    stage = Column(String(50), nullable=False)
    progress = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    completed_at = Column(String(50), nullable=True)
    deleted_at = Column(String(50), nullable=True)
    message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    canonical_document_id = Column(String(36), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="ingest_jobs")
    source = relationship("IngestSource", back_populates="ingest_jobs")
    
    __table_args__ = (
        Index("idx_ingest_jobs_project", "project_id"),
        Index("idx_ingest_jobs_source", "source_id"),
    )


class IdeaTicket(Base):
    """Idea ticket - feature requests and tasks derived from ideas."""
    __tablename__ = "idea_tickets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    cluster_id = Column(String(36), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    origin_idea_ids_json = Column(Text, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="idea_tickets")
    gap_suggestions = relationship("GapSuggestion", back_populates="ticket", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_idea_tickets_project", "project_id"),
    )


class KnowledgeNode(Base):
    """Knowledge node - semantic knowledge graph nodes."""
    __tablename__ = "knowledge_nodes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="knowledge_nodes")
    
    __table_args__ = (
        Index("idx_knowledge_nodes_project", "project_id"),
    )


class AgentRun(Base):
    """Agent run - tracks AI agent execution sessions."""
    __tablename__ = "agent_runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    agent_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    input_prompt = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    started_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    finished_at = Column(String(50), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="agent_runs")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")
    messages = relationship("AgentMessage", back_populates="run", cascade="all, delete-orphan")
    node_states = relationship("AgentNodeState", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_agent_runs_project", "project_id"),
    )


class IdeaCandidate(Base):
    """Idea candidate - extracted ideas from documents."""
    __tablename__ = "idea_candidates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False, default="")
    source_id = Column(String(36), ForeignKey("ingest_sources.id"), nullable=False)
    source_doc_id = Column(String(36), nullable=False)
    source_doc_chunk_id = Column(String(36), nullable=False)
    original_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="active")
    confidence = Column(Float, nullable=True, default=0.85)
    embedding_json = Column(Text, nullable=True)
    cluster_id = Column(String(36), nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="idea_candidates")
    source = relationship("IngestSource", back_populates="idea_candidates")
    
    __table_args__ = (
        Index("idx_idea_candidates_project", "project_id"),
        Index("idx_idea_candidates_cluster", "cluster_id"),
    )


class IdeaCluster(Base):
    """Idea cluster - groups of related ideas."""
    __tablename__ = "idea_clusters"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    idea_ids_json = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="idea_clusters")
    
    __table_args__ = (
        Index("idx_idea_clusters_project", "project_id"),
    )


class Roadmap(Base):
    """Roadmap - project planning graphs."""
    __tablename__ = "roadmaps"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    graph_json = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="roadmaps")
    
    __table_args__ = (
        Index("idx_roadmaps_project", "project_id"),
    )


class ContextItem(Base):
    """Context item - items in the agent context window."""
    __tablename__ = "context_items"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    tokens = Column(Integer, nullable=False, default=0)
    pinned = Column(Integer, nullable=False, default=0)
    canonical_document_id = Column(String(36), nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="context_items")
    
    __table_args__ = (
        Index("idx_context_items_project", "project_id"),
        Index("idx_context_items_pinned", "pinned"),
    )


class AgentStep(Base):
    """Agent step - individual steps within an agent run."""
    __tablename__ = "agent_steps"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    node_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    completed_at = Column(String(50), nullable=True)
    
    # Relationships
    run = relationship("AgentRun", back_populates="steps")
    
    __table_args__ = (
        Index("idx_agent_steps_run", "run_id"),
        Index("idx_agent_steps_step_number", "run_id", "step_number"),
    )


class AgentMessage(Base):
    """Agent message - messages within an agent run."""
    __tablename__ = "agent_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    context_item_ids_json = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    run = relationship("AgentRun", back_populates="messages")
    
    __table_args__ = (
        Index("idx_agent_messages_run", "run_id"),
        Index("idx_agent_messages_created_at", "run_id", "created_at"),
    )


class AgentNodeState(Base):
    """Agent node state - state of nodes in agent execution graph."""
    __tablename__ = "agent_node_states"
    
    run_id = Column(String(36), ForeignKey("agent_runs.id"), primary_key=True)
    node_id = Column(String(255), primary_key=True)
    status = Column(String(50), nullable=False)
    progress = Column(Float, nullable=False, default=0.0)
    messages_json = Column(Text, nullable=True)
    started_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)
    error = Column(Text, nullable=True)
    
    # Relationships
    run = relationship("AgentRun", back_populates="node_states")
    
    __table_args__ = (
        Index("idx_agent_node_states_run", "run_id"),
    )


class WorkflowGraph(Base):
    """Workflow graph - reusable workflow definitions."""
    __tablename__ = "workflow_graphs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    graph_json = Column(Text, nullable=False)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="workflow_graphs")
    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_workflow_graphs_project", "project_id"),
    )


class WorkflowRun(Base):
    """Workflow run - execution instance of a workflow."""
    __tablename__ = "workflow_runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    workflow_id = Column(String(36), ForeignKey("workflow_graphs.id"), nullable=False)
    status = Column(String(50), nullable=False)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    started_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    finished_at = Column(String(50), nullable=True)
    last_message = Column(Text, nullable=True)
    task_id = Column(String(255), nullable=True)
    checkpoint_json = Column(Text, nullable=True)
    paused_at = Column(String(50), nullable=True)
    cancelled_at = Column(String(50), nullable=True)
    estimated_completion = Column(String(50), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="workflow_runs")
    workflow = relationship("WorkflowGraph", back_populates="runs")
    node_states = relationship("WorkflowNodeState", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_workflow_runs_project", "project_id"),
        Index("idx_workflow_runs_status", "status"),
        Index("idx_workflow_runs_task_id", "task_id"),
    )


class WorkflowNodeState(Base):
    """Workflow node state - state of nodes in workflow execution."""
    __tablename__ = "workflow_node_states"
    
    run_id = Column(String(36), ForeignKey("workflow_runs.id"), primary_key=True)
    node_id = Column(String(255), primary_key=True)
    status = Column(String(50), nullable=False)
    progress = Column(Float, nullable=False, default=0.0)
    messages_json = Column(Text, nullable=True)
    started_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)
    error = Column(Text, nullable=True)
    
    # Relationships
    run = relationship("WorkflowRun", back_populates="node_states")
    
    __table_args__ = (
        Index("idx_workflow_node_states_run", "run_id"),
    )


class RoadmapNode(Base):
    """Roadmap node - nodes in project roadmap graph."""
    __tablename__ = "roadmap_nodes"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    node_type = Column(String(50), nullable=False, default="task")
    priority = Column(String(50), nullable=True)
    metadata_json = Column(Text, nullable=True)
    start_date = Column(String(50), nullable=True)
    target_date = Column(String(50), nullable=True)
    depends_on_ids_json = Column(Text, nullable=True)
    lane_id = Column(String(36), nullable=True)
    idea_id = Column(String(36), nullable=True)
    ticket_id = Column(String(36), nullable=True)
    mission_control_task_id = Column(String(255), nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    updated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="roadmap_nodes")
    
    __table_args__ = (
        Index("idx_roadmap_nodes_project", "project_id"),
        Index("idx_roadmap_nodes_status", "status"),
    )


class RoadmapEdge(Base):
    """Roadmap edge - edges connecting roadmap nodes."""
    __tablename__ = "roadmap_edges"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    from_node_id = Column(String(36), ForeignKey("roadmap_nodes.id"), nullable=False)
    to_node_id = Column(String(36), ForeignKey("roadmap_nodes.id"), nullable=False)
    kind = Column(String(50), nullable=False)
    label = Column(String(255), nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="roadmap_edges")
    
    __table_args__ = (
        Index("idx_roadmap_edges_project", "project_id"),
        Index("idx_roadmap_edges_from", "from_node_id"),
        Index("idx_roadmap_edges_to", "to_node_id"),
    )


class KnowledgeEdge(Base):
    """Knowledge edge - edges in knowledge graph."""
    __tablename__ = "knowledge_edges"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    source = Column(String(36), ForeignKey("knowledge_nodes.id"), nullable=False)
    target = Column(String(36), ForeignKey("knowledge_nodes.id"), nullable=False)
    type = Column(String(50), nullable=False)
    weight = Column(Float, nullable=True)
    label = Column(String(255), nullable=True)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="knowledge_edges")
    
    __table_args__ = (
        Index("idx_knowledge_edges_project", "project_id"),
        Index("idx_knowledge_edges_source", "source"),
        Index("idx_knowledge_edges_target", "target"),
    )


class GapReport(Base):
    """Gap report - analysis reports for project gaps."""
    __tablename__ = "gap_reports"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    generated_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="gap_reports")
    suggestions = relationship("GapSuggestion", back_populates="report", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_gap_reports_project", "project_id"),
    )


class GapSuggestion(Base):
    """Gap suggestion - individual suggestions from gap analysis."""
    __tablename__ = "gap_suggestions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("gap_reports.id"), nullable=False)
    project_id = Column(String(36), nullable=False)
    ticket_id = Column(String(36), ForeignKey("idea_tickets.id"), nullable=False)
    status = Column(String(50), nullable=False)
    notes = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    related_files_json = Column(Text, nullable=True)
    
    # Relationships
    report = relationship("GapReport", back_populates="suggestions")
    ticket = relationship("IdeaTicket", back_populates="gap_suggestions")
    
    __table_args__ = (
        Index("idx_gap_suggestions_report", "report_id"),
    )


class ChatSegment(Base):
    """Chat segment - conversation history segments."""
    __tablename__ = "chat_segments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    chat_id = Column(String(36), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())
    
    # Relationships
    project = relationship("Project", back_populates="chat_segments")
    
    __table_args__ = (
        Index("idx_chat_segments_project", "project_id"),
    )


class SchemaMigration(Base):
    """Schema migration - tracks applied migrations."""
    __tablename__ = "schema_migrations"
    
    version = Column(String(50), primary_key=True)
    applied_at = Column(String(50), nullable=False, default=lambda: utcnow().isoformat())

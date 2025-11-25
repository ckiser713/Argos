from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings


def _db_path() -> Path:
    settings = get_settings()
    path = Path(settings.atlas_db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create base tables required for atlas.db if they do not exist."""
    with db_session() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                default_model_role_id TEXT,
                root_idea_cluster_id TEXT,
                roadmap_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);

            CREATE TABLE IF NOT EXISTS ingest_sources (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                uri TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_ingest_sources_project ON ingest_sources(project_id);

            CREATE TABLE IF NOT EXISTS ingest_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                byte_size INTEGER NOT NULL DEFAULT 0,
                mime_type TEXT,
                is_deep_scan INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                canonical_document_id TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(source_id) REFERENCES ingest_sources(id)
            );
            CREATE INDEX IF NOT EXISTS idx_ingest_jobs_project ON ingest_jobs(project_id);
            CREATE INDEX IF NOT EXISTS idx_ingest_jobs_source ON ingest_jobs(source_id);

            CREATE TABLE IF NOT EXISTS idea_tickets (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                cluster_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                origin_idea_ids_json TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_idea_tickets_project ON idea_tickets(project_id);

            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                tags_json TEXT,
                type TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_project ON knowledge_nodes(project_id);

            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL,
                input_prompt TEXT,
                output_summary TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_runs_project ON agent_runs(project_id);

            CREATE TABLE IF NOT EXISTS idea_candidates (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_doc_id TEXT NOT NULL,
                source_doc_chunk_id TEXT NOT NULL,
                original_text TEXT NOT NULL,
                summary TEXT NOT NULL,
                embedding_json TEXT,
                cluster_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(source_id) REFERENCES ingest_sources(id)
            );
            CREATE INDEX IF NOT EXISTS idx_idea_candidates_project ON idea_candidates(project_id);
            CREATE INDEX IF NOT EXISTS idx_idea_candidates_cluster ON idea_candidates(cluster_id);

            CREATE TABLE IF NOT EXISTS idea_clusters (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                summary TEXT NOT NULL,
                idea_ids_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_idea_clusters_project ON idea_clusters(project_id);

            CREATE TABLE IF NOT EXISTS roadmaps (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                graph_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_roadmaps_project ON roadmaps(project_id);

            CREATE TABLE IF NOT EXISTS context_items (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                tokens INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0,
                canonical_document_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_context_items_project ON context_items(project_id);
            CREATE INDEX IF NOT EXISTS idx_context_items_pinned ON context_items(pinned);

            CREATE TABLE IF NOT EXISTS agent_steps (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                node_id TEXT,
                status TEXT NOT NULL,
                input_json TEXT,
                output_json TEXT,
                error TEXT,
                duration_ms INTEGER,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY(run_id) REFERENCES agent_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps(run_id);
            CREATE INDEX IF NOT EXISTS idx_agent_steps_step_number ON agent_steps(run_id, step_number);

            CREATE TABLE IF NOT EXISTS agent_messages (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_item_ids_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES agent_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_messages_run ON agent_messages(run_id);
            CREATE INDEX IF NOT EXISTS idx_agent_messages_created_at ON agent_messages(run_id, created_at);

            CREATE TABLE IF NOT EXISTS agent_node_states (
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0,
                messages_json TEXT,
                started_at TEXT,
                completed_at TEXT,
                error TEXT,
                PRIMARY KEY (run_id, node_id),
                FOREIGN KEY(run_id) REFERENCES agent_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_agent_node_states_run ON agent_node_states(run_id);

            CREATE TABLE IF NOT EXISTS workflow_graphs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                graph_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_graphs_project ON workflow_graphs(project_id);

            CREATE TABLE IF NOT EXISTS workflow_runs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                input_json TEXT,
                output_json TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                last_message TEXT,
                task_id TEXT,
                checkpoint_json TEXT,
                paused_at TEXT,
                cancelled_at TEXT,
                estimated_completion TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(workflow_id) REFERENCES workflow_graphs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_runs_project ON workflow_runs(project_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
            CREATE INDEX IF NOT EXISTS idx_workflow_runs_task_id ON workflow_runs(task_id);

            CREATE TABLE IF NOT EXISTS workflow_node_states (
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0,
                messages_json TEXT,
                started_at TEXT,
                completed_at TEXT,
                error TEXT,
                PRIMARY KEY (run_id, node_id),
                FOREIGN KEY(run_id) REFERENCES workflow_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_workflow_node_states_run ON workflow_node_states(run_id);

            CREATE TABLE IF NOT EXISTS roadmap_nodes (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                label TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                priority TEXT,
                start_date TEXT,
                target_date TEXT,
                depends_on_ids_json TEXT,
                lane_id TEXT,
                idea_id TEXT,
                ticket_id TEXT,
                mission_control_task_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_roadmap_nodes_project ON roadmap_nodes(project_id);
            CREATE INDEX IF NOT EXISTS idx_roadmap_nodes_status ON roadmap_nodes(status);

            CREATE TABLE IF NOT EXISTS roadmap_edges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                from_node_id TEXT NOT NULL,
                to_node_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                label TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(from_node_id) REFERENCES roadmap_nodes(id),
                FOREIGN KEY(to_node_id) REFERENCES roadmap_nodes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_roadmap_edges_project ON roadmap_edges(project_id);
            CREATE INDEX IF NOT EXISTS idx_roadmap_edges_from ON roadmap_edges(from_node_id);
            CREATE INDEX IF NOT EXISTS idx_roadmap_edges_to ON roadmap_edges(to_node_id);

            CREATE TABLE IF NOT EXISTS knowledge_edges (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                type TEXT NOT NULL,
                weight REAL,
                label TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(source) REFERENCES knowledge_nodes(id),
                FOREIGN KEY(target) REFERENCES knowledge_nodes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_edges_project ON knowledge_edges(project_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_edges_source ON knowledge_edges(source);
            CREATE INDEX IF NOT EXISTS idx_knowledge_edges_target ON knowledge_edges(target);

            CREATE TABLE IF NOT EXISTS gap_reports (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_gap_reports_project ON gap_reports(project_id);

            CREATE TABLE IF NOT EXISTS gap_suggestions (
                id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL,
                confidence REAL NOT NULL,
                related_files_json TEXT,
                FOREIGN KEY(report_id) REFERENCES gap_reports(id),
                FOREIGN KEY(ticket_id) REFERENCES idea_tickets(id)
            );
            CREATE INDEX IF NOT EXISTS idx_gap_suggestions_report ON gap_suggestions(report_id);
            """
        )
        conn.commit()

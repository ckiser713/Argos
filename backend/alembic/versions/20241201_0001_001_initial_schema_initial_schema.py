"""Initial schema for Cortex backend

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-12-01

This migration creates all tables matching the existing SQLite schema,
now compatible with PostgreSQL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('slug', sa.String(255), unique=True, nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
        sa.Column('default_model_role_id', sa.String(36), nullable=True),
        sa.Column('root_idea_cluster_id', sa.String(36), nullable=True),
        sa.Column('roadmap_id', sa.String(36), nullable=True),
    )
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_slug', 'projects', ['slug'])

    # Ingest Sources table
    op.create_table(
        'ingest_sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('uri', sa.Text, nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_ingest_sources_project', 'ingest_sources', ['project_id'])

    # Ingest Jobs table
    op.create_table(
        'ingest_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source_path', sa.Text, nullable=True),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('ingest_sources.id'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('byte_size', sa.Integer, nullable=False, server_default='0'),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('is_deep_scan', sa.Integer, nullable=False, server_default='0'),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('progress', sa.Float, nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
        sa.Column('completed_at', sa.String(50), nullable=True),
        sa.Column('deleted_at', sa.String(50), nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('canonical_document_id', sa.String(36), nullable=True),
    )
    op.create_index('idx_ingest_jobs_project', 'ingest_jobs', ['project_id'])
    op.create_index('idx_ingest_jobs_source', 'ingest_jobs', ['source_id'])

    # Idea Tickets table
    op.create_table(
        'idea_tickets',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('cluster_id', sa.String(36), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
        sa.Column('origin_idea_ids_json', sa.Text, nullable=True),
    )
    op.create_index('idx_idea_tickets_project', 'idea_tickets', ['project_id'])

    # Knowledge Nodes table
    op.create_table(
        'knowledge_nodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('text', sa.Text, nullable=True),
        sa.Column('tags_json', sa.Text, nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('metadata_json', sa.Text, nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=True),
    )
    op.create_index('idx_knowledge_nodes_project', 'knowledge_nodes', ['project_id'])

    # Agent Runs table
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('input_prompt', sa.Text, nullable=True),
        sa.Column('output_summary', sa.Text, nullable=True),
        sa.Column('started_at', sa.String(50), nullable=False),
        sa.Column('finished_at', sa.String(50), nullable=True),
    )
    op.create_index('idx_agent_runs_project', 'agent_runs', ['project_id'])

    # Idea Candidates table
    op.create_table(
        'idea_candidates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False, server_default=''),
        sa.Column('source_id', sa.String(36), sa.ForeignKey('ingest_sources.id'), nullable=False),
        sa.Column('source_doc_id', sa.String(36), nullable=False),
        sa.Column('source_doc_chunk_id', sa.String(36), nullable=False),
        sa.Column('original_text', sa.Text, nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('confidence', sa.Float, nullable=True, server_default='0.85'),
        sa.Column('embedding_json', sa.Text, nullable=True),
        sa.Column('cluster_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_idea_candidates_project', 'idea_candidates', ['project_id'])
    op.create_index('idx_idea_candidates_cluster', 'idea_candidates', ['cluster_id'])

    # Idea Clusters table
    op.create_table(
        'idea_clusters',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('idea_ids_json', sa.Text, nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_idea_clusters_project', 'idea_clusters', ['project_id'])

    # Roadmaps table
    op.create_table(
        'roadmaps',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('graph_json', sa.Text, nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_roadmaps_project', 'roadmaps', ['project_id'])

    # Context Items table
    op.create_table(
        'context_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('pinned', sa.Integer, nullable=False, server_default='0'),
        sa.Column('canonical_document_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_context_items_project', 'context_items', ['project_id'])
    op.create_index('idx_context_items_pinned', 'context_items', ['pinned'])

    # Agent Steps table
    op.create_table(
        'agent_steps',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('agent_runs.id'), nullable=False),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('node_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('input_json', sa.Text, nullable=True),
        sa.Column('output_json', sa.Text, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('started_at', sa.String(50), nullable=False),
        sa.Column('completed_at', sa.String(50), nullable=True),
    )
    op.create_index('idx_agent_steps_run', 'agent_steps', ['run_id'])
    op.create_index('idx_agent_steps_step_number', 'agent_steps', ['run_id', 'step_number'])

    # Agent Messages table
    op.create_table(
        'agent_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('agent_runs.id'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('context_item_ids_json', sa.Text, nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_agent_messages_run', 'agent_messages', ['run_id'])
    op.create_index('idx_agent_messages_created_at', 'agent_messages', ['run_id', 'created_at'])

    # Agent Node States table
    op.create_table(
        'agent_node_states',
        sa.Column('run_id', sa.String(36), sa.ForeignKey('agent_runs.id'), primary_key=True),
        sa.Column('node_id', sa.String(255), primary_key=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('progress', sa.Float, nullable=False, server_default='0'),
        sa.Column('messages_json', sa.Text, nullable=True),
        sa.Column('started_at', sa.String(50), nullable=True),
        sa.Column('completed_at', sa.String(50), nullable=True),
        sa.Column('error', sa.Text, nullable=True),
    )
    op.create_index('idx_agent_node_states_run', 'agent_node_states', ['run_id'])

    # Workflow Graphs table
    op.create_table(
        'workflow_graphs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('graph_json', sa.Text, nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_workflow_graphs_project', 'workflow_graphs', ['project_id'])

    # Workflow Runs table
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('workflow_graphs.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('input_json', sa.Text, nullable=True),
        sa.Column('output_json', sa.Text, nullable=True),
        sa.Column('started_at', sa.String(50), nullable=False),
        sa.Column('finished_at', sa.String(50), nullable=True),
        sa.Column('last_message', sa.Text, nullable=True),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('checkpoint_json', sa.Text, nullable=True),
        sa.Column('paused_at', sa.String(50), nullable=True),
        sa.Column('cancelled_at', sa.String(50), nullable=True),
        sa.Column('estimated_completion', sa.String(50), nullable=True),
    )
    op.create_index('idx_workflow_runs_project', 'workflow_runs', ['project_id'])
    op.create_index('idx_workflow_runs_status', 'workflow_runs', ['status'])
    op.create_index('idx_workflow_runs_task_id', 'workflow_runs', ['task_id'])

    # Workflow Node States table
    op.create_table(
        'workflow_node_states',
        sa.Column('run_id', sa.String(36), sa.ForeignKey('workflow_runs.id'), primary_key=True),
        sa.Column('node_id', sa.String(255), primary_key=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('progress', sa.Float, nullable=False, server_default='0'),
        sa.Column('messages_json', sa.Text, nullable=True),
        sa.Column('started_at', sa.String(50), nullable=True),
        sa.Column('completed_at', sa.String(50), nullable=True),
        sa.Column('error', sa.Text, nullable=True),
    )
    op.create_index('idx_workflow_node_states_run', 'workflow_node_states', ['run_id'])

    # Roadmap Nodes table
    op.create_table(
        'roadmap_nodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('node_type', sa.String(50), nullable=False, server_default='task'),
        sa.Column('priority', sa.String(50), nullable=True),
        sa.Column('metadata_json', sa.Text, nullable=True),
        sa.Column('start_date', sa.String(50), nullable=True),
        sa.Column('target_date', sa.String(50), nullable=True),
        sa.Column('depends_on_ids_json', sa.Text, nullable=True),
        sa.Column('lane_id', sa.String(36), nullable=True),
        sa.Column('idea_id', sa.String(36), nullable=True),
        sa.Column('ticket_id', sa.String(36), nullable=True),
        sa.Column('mission_control_task_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_roadmap_nodes_project', 'roadmap_nodes', ['project_id'])
    op.create_index('idx_roadmap_nodes_status', 'roadmap_nodes', ['status'])

    # Roadmap Edges table
    op.create_table(
        'roadmap_edges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('from_node_id', sa.String(36), sa.ForeignKey('roadmap_nodes.id'), nullable=False),
        sa.Column('to_node_id', sa.String(36), sa.ForeignKey('roadmap_nodes.id'), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_roadmap_edges_project', 'roadmap_edges', ['project_id'])
    op.create_index('idx_roadmap_edges_from', 'roadmap_edges', ['from_node_id'])
    op.create_index('idx_roadmap_edges_to', 'roadmap_edges', ['to_node_id'])

    # Knowledge Edges table
    op.create_table(
        'knowledge_edges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('source', sa.String(36), sa.ForeignKey('knowledge_nodes.id'), nullable=False),
        sa.Column('target', sa.String(36), sa.ForeignKey('knowledge_nodes.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('weight', sa.Float, nullable=True),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_knowledge_edges_project', 'knowledge_edges', ['project_id'])
    op.create_index('idx_knowledge_edges_source', 'knowledge_edges', ['source'])
    op.create_index('idx_knowledge_edges_target', 'knowledge_edges', ['target'])

    # Gap Reports table
    op.create_table(
        'gap_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('generated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_gap_reports_project', 'gap_reports', ['project_id'])

    # Gap Suggestions table
    op.create_table(
        'gap_suggestions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('report_id', sa.String(36), sa.ForeignKey('gap_reports.id'), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('ticket_id', sa.String(36), sa.ForeignKey('idea_tickets.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('related_files_json', sa.Text, nullable=True),
    )
    op.create_index('idx_gap_suggestions_report', 'gap_suggestions', ['report_id'])

    # Chat Segments table
    op.create_table(
        'chat_segments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('chat_id', sa.String(36), nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_chat_segments_project', 'chat_segments', ['project_id'])

    # Schema Migrations table
    op.create_table(
        'schema_migrations',
        sa.Column('version', sa.String(50), primary_key=True),
        sa.Column('applied_at', sa.String(50), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting FK constraints)
    op.drop_table('schema_migrations')
    op.drop_table('chat_segments')
    op.drop_table('gap_suggestions')
    op.drop_table('gap_reports')
    op.drop_table('knowledge_edges')
    op.drop_table('roadmap_edges')
    op.drop_table('roadmap_nodes')
    op.drop_table('workflow_node_states')
    op.drop_table('workflow_runs')
    op.drop_table('workflow_graphs')
    op.drop_table('agent_node_states')
    op.drop_table('agent_messages')
    op.drop_table('agent_steps')
    op.drop_table('context_items')
    op.drop_table('roadmaps')
    op.drop_table('idea_clusters')
    op.drop_table('idea_candidates')
    op.drop_table('agent_runs')
    op.drop_table('knowledge_nodes')
    op.drop_table('idea_tickets')
    op.drop_table('ingest_jobs')
    op.drop_table('ingest_sources')
    op.drop_table('projects')

"""
Alembic Environment Configuration for Cortex Backend.

This module configures Alembic to use Cortex's SQLAlchemy models and database settings.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Cortex configuration and models
from app.config import get_settings
from app.database import Base
from app.models import (
    Project, IngestSource, IngestJob, IdeaTicket, KnowledgeNode,
    AgentRun, IdeaCandidate, IdeaCluster, Roadmap, ContextItem,
    AgentStep, AgentMessage, AgentNodeState, WorkflowGraph, WorkflowRun,
    WorkflowNodeState, RoadmapNode, RoadmapEdge, KnowledgeEdge,
    GapReport, GapSuggestion, ChatSegment, SchemaMigration,
    AuthUser, AuthRefreshToken, AuthTokenBlacklist,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from SQLAlchemy models
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get the database URL from Cortex configuration."""
    settings = get_settings()
    url = settings.database_url
    
    # For sync Alembic operations, use psycopg2 driver
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://")
    
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    # Override sqlalchemy.url with Cortex configuration
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Add durable ingest storage/queue fields

Revision ID: 003_ingest_durable_pipeline
Revises: 002_auth_tables
Create Date: 2024-12-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_ingest_durable_pipeline"
down_revision: Union[str, None] = "002_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ingest_jobs", sa.Column("source_uri", sa.Text(), nullable=True))
    op.add_column("ingest_jobs", sa.Column("checksum", sa.String(length=128), nullable=True))
    op.add_column("ingest_jobs", sa.Column("started_at", sa.String(length=50), nullable=True))
    op.add_column("ingest_jobs", sa.Column("task_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_jobs", "task_id")
    op.drop_column("ingest_jobs", "started_at")
    op.drop_column("ingest_jobs", "checksum")
    op.drop_column("ingest_jobs", "source_uri")


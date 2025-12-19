"""Add auth users and token tables

Revision ID: 002_auth_tables
Revises: 001_initial_schema
Create Date: 2024-12-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_auth_tables"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("roles", sa.String(length=255), nullable=False, server_default="user"),
        sa.Column("scopes", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_users_username", "auth_users", ["username"], unique=True)

    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
    )
    op.create_index("idx_auth_refresh_tokens_user", "auth_refresh_tokens", ["user_id"])
    op.create_index("idx_auth_refresh_tokens_expires", "auth_refresh_tokens", ["expires_at"])

    op.create_table(
        "auth_token_blacklist",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("jti", sa.String(length=64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("auth_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_type", sa.String(length=20), nullable=False, server_default="access"),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_auth_blacklist_jti", "auth_token_blacklist", ["jti"])
    op.create_index("idx_auth_blacklist_user", "auth_token_blacklist", ["user_id"])
    op.create_index("idx_auth_blacklist_expires", "auth_token_blacklist", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_auth_blacklist_expires", table_name="auth_token_blacklist")
    op.drop_index("idx_auth_blacklist_user", table_name="auth_token_blacklist")
    op.drop_index("idx_auth_blacklist_jti", table_name="auth_token_blacklist")
    op.drop_table("auth_token_blacklist")

    op.drop_index("idx_auth_refresh_tokens_expires", table_name="auth_refresh_tokens")
    op.drop_index("idx_auth_refresh_tokens_user", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")

    op.drop_index("ix_auth_users_username", table_name="auth_users")
    op.drop_table("auth_users")


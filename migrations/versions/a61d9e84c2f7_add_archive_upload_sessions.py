"""add resumable archive upload sessions

Revision ID: a61d9e84c2f7
Revises: f3a91c6d2e44
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a61d9e84c2f7"
down_revision: str | Sequence[str] | None = "f3a91c6d2e44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "archive_upload_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "archive_entry_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("archive_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "received_bytes",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["archive_entry_id"], ["archive_entries.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["archive_asset_id"], ["archive_assets.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_archive_upload_sessions_entry_status",
        "archive_upload_sessions",
        ["archive_entry_id", "status"],
    )
    op.create_index(
        "ix_archive_upload_sessions_creator_created",
        "archive_upload_sessions",
        ["created_by_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_archive_upload_sessions_creator_created",
        table_name="archive_upload_sessions",
    )
    op.drop_index(
        "ix_archive_upload_sessions_entry_status",
        table_name="archive_upload_sessions",
    )
    op.drop_table("archive_upload_sessions")

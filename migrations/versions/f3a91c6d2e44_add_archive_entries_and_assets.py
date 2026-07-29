"""add archive entries, downloadable assets, and import jobs

Revision ID: f3a91c6d2e44
Revises: 02a3779a40ff
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f3a91c6d2e44"
down_revision: str | Sequence[str] | None = "02a3779a40ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "archive_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("domain_id", sa.BigInteger(), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "external_key",
            name="uq_archive_entry_document_external_key",
        ),
    )
    op.create_index(
        "ix_archive_entries_domain_id", "archive_entries", ["domain_id"]
    )
    op.create_index(
        "ix_archive_entries_document_ordinal",
        "archive_entries",
        ["document_id", "ordinal"],
    )

    op.create_table(
        "archive_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archive_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="ready",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["archive_entry_id"], ["archive_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "archive_entry_id",
            "original_filename",
            name="uq_archive_asset_entry_filename",
        ),
    )
    op.create_index(
        "ix_archive_assets_archive_entry_id",
        "archive_assets",
        ["archive_entry_id"],
    )
    op.create_index("ix_archive_assets_sha256", "archive_assets", ["sha256"])

    op.create_table(
        "archive_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("source_filename", sa.String(length=512), nullable=False),
        sa.Column(
            "duplicate_strategy",
            sa.String(length=32),
            server_default="reject",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("total_entries", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "processed_entries", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "succeeded_entries", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("failed_entries", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "error_summary",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_archive_import_jobs_status_created_at",
        "archive_import_jobs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_archive_import_jobs_status_created_at",
        table_name="archive_import_jobs",
    )
    op.drop_table("archive_import_jobs")
    op.drop_index("ix_archive_assets_sha256", table_name="archive_assets")
    op.drop_index(
        "ix_archive_assets_archive_entry_id", table_name="archive_assets"
    )
    op.drop_table("archive_assets")
    op.drop_index(
        "ix_archive_entries_document_ordinal", table_name="archive_entries"
    )
    op.drop_index("ix_archive_entries_domain_id", table_name="archive_entries")
    op.drop_table("archive_entries")

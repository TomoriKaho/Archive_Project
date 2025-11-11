"""add vector indexing progress fields to documents

Revision ID: 2c3f5fbc3f52
Revises: 4f8b6d1f9af0
Create Date: 2025-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2c3f5fbc3f52"
down_revision: Union[str, None] = "4f8b6d1f9af0"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Add progress columns used to report vector indexing state."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("documents")}

    if "vector_index_status" not in existing_columns:
        op.add_column(
            "documents",
            sa.Column(
                "vector_index_status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            ),
        )

    if "vector_indexed_chunks" not in existing_columns:
        op.add_column(
            "documents",
            sa.Column("vector_indexed_chunks", sa.Integer(), nullable=False, server_default="0"),
        )

    if "vector_total_chunks" not in existing_columns:
        op.add_column(
            "documents",
            sa.Column("vector_total_chunks", sa.Integer(), nullable=False, server_default="0"),
        )

    if "vector_index_error" not in existing_columns:
        op.add_column(
            "documents",
            sa.Column("vector_index_error", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Remove progress columns when rolling back."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("documents")}

    for column_name in (
        "vector_index_error",
        "vector_total_chunks",
        "vector_indexed_chunks",
        "vector_index_status",
    ):
        if column_name in existing_columns:
            op.drop_column("documents", column_name)

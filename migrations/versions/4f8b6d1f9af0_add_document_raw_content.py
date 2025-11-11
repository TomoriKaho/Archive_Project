"""add raw content column to documents

Revision ID: 4f8b6d1f9af0
Revises: c8e3d53e366c
Create Date: 2024-05-08 00:00:00.000000
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f8b6d1f9af0"
down_revision: Union[str, None] = "c8e3d53e366c"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Add the raw_content column so we can preserve the original document."""
    op.add_column(
        "documents",
        sa.Column("raw_content", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("documents", "raw_content", server_default=None)


def downgrade() -> None:
    """Drop the raw_content column when rolling back."""
    op.drop_column("documents", "raw_content")

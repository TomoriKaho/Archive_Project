"""add language column to domains

Revision ID: 9b2f6c8d1f3a
Revises: 2c3f5fbc3f52
Create Date: 2025-01-15 00:00:00.000000
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b2f6c8d1f3a"
down_revision: Union[str, None] = "2c3f5fbc3f52"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Add the language column to domains with a default for existing rows."""
    op.add_column(
        "domains",
        sa.Column("language", sa.String(length=10), nullable=True, server_default="zh"),
    )
    op.alter_column("domains", "language", server_default=None)


def downgrade() -> None:
    """Drop the language column from domains when rolling back."""
    op.drop_column("domains", "language")

"""add message_metadata column to messages"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c2b7f1e1d9c"
down_revision: Union[str, Sequence[str], None] = "8dca4f9d1b2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the metadata JSON column."""

    op.add_column(
        "messages",
        sa.Column(
            "message_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("messages", "message_metadata", server_default=None)


def downgrade() -> None:
    """Remove the metadata column."""

    op.drop_column("messages", "message_metadata")


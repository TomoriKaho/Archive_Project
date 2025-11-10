"""remove tag metadata from documents

Revision ID: c8e3d53e366c
Revises: 8dca4f9d1b2d
Create Date: 2025-10-16 00:00:00.000000

"""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c8e3d53e366c"
down_revision: Union[str, None] = "8dca4f9d1b2d"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Remove the legacy tags key from document metadata."""
    bind = op.get_bind()
    documents = sa.table(
        "documents",
        sa.column("id", sa.BigInteger),
        sa.column("doc_metadata", sa.JSON),
    )
    rows = bind.execute(sa.select(documents.c.id, documents.c.doc_metadata)).all()
    for row in rows:
        metadata = row.doc_metadata or {}
        if isinstance(metadata, dict) and "tags" in metadata:
            cleaned = {key: value for key, value in metadata.items() if key != "tags"}
            bind.execute(
                sa.update(documents)
                .where(documents.c.id == row.id)
                .values(doc_metadata=cleaned)
            )


def downgrade() -> None:
    """Nothing to restore for removed tags."""
    # No-op: tag metadata has been permanently removed.

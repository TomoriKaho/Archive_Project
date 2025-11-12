"""Remove domain/title unique constraint from documents."""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7b1dcb0f3a43"
down_revision: Union[str, None] = "3f2c1d4b8e90"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Drop the composite unique constraint to allow duplicate titles."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("documents")
    }
    if "uq_documents_domain_title" in existing:
        op.drop_constraint(
            "uq_documents_domain_title",
            "documents",
            type_="unique",
        )


def downgrade() -> None:
    """Re-create the composite unique constraint if rolling back."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("documents")
    }
    if "uq_documents_domain_title" not in existing:
        op.create_unique_constraint(
            "uq_documents_domain_title",
            "documents",
            ["domain_id", "title"],
        )

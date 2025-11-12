"""Enforce unique document titles per domain."""
from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3f2c1d4b8e90"
down_revision: Union[str, None] = "2c3f5fbc3f52"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Add the composite unique constraint when missing."""

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


def downgrade() -> None:
    """Drop the composite unique constraint when rolling back."""

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

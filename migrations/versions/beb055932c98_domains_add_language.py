"""domains add language

Revision ID: beb055932c98
Revises: 7b1dcb0f3a43
Create Date: 2026-01-27 11:50:40
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "beb055932c98"
down_revision = "7b1dcb0f3a43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add language column with a default to keep existing rows valid
    op.add_column(
        "domains",
        sa.Column("language", sa.String(length=10), nullable=True, server_default="zh"),
    )

    # Backfill existing rows (some DBs may not apply server_default to old rows)
    op.execute("UPDATE domains SET language='zh' WHERE language IS NULL")

    # Enforce NOT NULL and drop the default
    op.alter_column("domains", "language", nullable=False, server_default=None)


def downgrade() -> None:
    op.drop_column("domains", "language")
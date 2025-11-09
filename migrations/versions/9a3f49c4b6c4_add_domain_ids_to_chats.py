"""add domain_ids column to chats"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9a3f49c4b6c4"
down_revision = "9b4c38b6fa0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("domain_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chats", "domain_ids")

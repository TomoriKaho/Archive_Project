"""merge heads

Revision ID: ab99cfc8060c
Revises: 7b1dcb0f3a43, 9b2f6c8d1f3a
Create Date: 2026-01-13 01:56:59.834399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab99cfc8060c'
down_revision: Union[str, Sequence[str], None] = ('7b1dcb0f3a43', '9b2f6c8d1f3a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

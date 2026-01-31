"""Merge beb055932c98 with main

Revision ID: 02a3779a40ff
Revises: ab99cfc8060c, beb055932c98
Create Date: 2026-01-31 07:43:12.859919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02a3779a40ff'
down_revision: Union[str, Sequence[str], None] = ('ab99cfc8060c', 'beb055932c98')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

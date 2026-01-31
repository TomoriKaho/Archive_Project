from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError

# revision identifiers, used by Alembic.
revision: str = "9b2f6c8d1f3a"
down_revision: str = "2c3f5fbc3f52"
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add the language column to domains with a default for existing rows."""
    bind = op.get_bind()
    
    # 使用 get_columns 来检查列是否存在
    columns = [column['name'] for column in inspect(bind).get_columns('domains')]
    
    if 'language' not in columns:
        op.add_column(
            'domains',
            sa.Column('language', sa.String(length=10), nullable=True, server_default='zh'),
        )
        op.alter_column('domains', 'language', server_default=None)
    else:
        print("Column 'language' already exists. Skipping.")

def downgrade() -> None:
    """Drop the language column from domains when rolling back."""
    op.drop_column('domains', 'language')

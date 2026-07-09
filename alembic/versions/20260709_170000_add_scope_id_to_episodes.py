"""Add scope_id to episodes

Revision ID: 20260709_170000
Revises: 20260709_162900
Create Date: 2026-07-09 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260709_170000'
down_revision: Union[str, None] = '20260709_162900'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('episodes', sa.Column('scope_id', sa.String(length=255), nullable=True))
    op.create_index('ix_episodes_scope_id', 'episodes', ['scope_id'])


def downgrade() -> None:
    op.drop_index('ix_episodes_scope_id', table_name='episodes')
    op.drop_column('episodes', 'scope_id')

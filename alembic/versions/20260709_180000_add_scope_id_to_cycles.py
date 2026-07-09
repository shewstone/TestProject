"""Add scope_id to cycles

Revision ID: 20260709_180000
Revises: 20260709_173000
Create Date: 2026-07-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260709_180000'
down_revision: Union[str, None] = '20260709_173000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cycles', sa.Column('scope_id', sa.String(length=255), nullable=True))
    op.create_index('ix_cycles_scope_id', 'cycles', ['scope_id'])


def downgrade() -> None:
    op.drop_index('ix_cycles_scope_id', table_name='cycles')
    op.drop_column('cycles', 'scope_id')

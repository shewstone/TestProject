"""Add mechanism_tags to episodes

Revision ID: 20260709_181500
Revises: 20260709_180000
Create Date: 2026-07-09 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260709_181500'
down_revision: Union[str, None] = '20260709_180000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('episodes', sa.Column('mechanism_tags', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    op.drop_column('episodes', 'mechanism_tags')

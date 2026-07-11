"""Add source_documents.chunks_processed: live per-chunk progress.

The watcher commits after every extracted chunk so the dashboard's
separate session can render progress during long LLM runs.

Revision ID: 20260711_100000
Revises: 20260710_140000
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260711_100000'
down_revision: Union[str, None] = '20260710_140000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "source_documents",
        sa.Column("chunks_processed", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("source_documents", "chunks_processed")

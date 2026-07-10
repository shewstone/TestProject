"""Add episodes.surface_embedding_epoch / structural_embedding_epoch (T4).

Backfill semantics matter here:
- Surface vectors embed raw title/summary text; the v0.7 render change did
  not touch them, so existing surface vectors are stamped with the CURRENT
  surface epoch (model id) and stay retrievable.
- Structural vectors were produced by the pre-v0.7 render, which design doc
  Sec 11.4 explicitly declares invalid. They are stamped with the old epoch
  ("render-v0.6.0+..."), which is BY DESIGN not the current one — they stop
  matching in retrieval until scripts re-embed them. A smaller honest analog
  base beats a larger corrupt one.

Revision ID: 20260710_123000
Revises: 20260710_120000
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260710_123000'
down_revision: Union[str, None] = '20260710_120000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRE_V07_STRUCTURAL_EPOCH = "render-v0.6.0+all-MiniLM-L6-v2"
CURRENT_SURFACE_EPOCH = "all-MiniLM-L6-v2"


def upgrade() -> None:
    op.add_column(
        "episodes",
        sa.Column("surface_embedding_epoch", sa.String(100), nullable=True),
    )
    op.add_column(
        "episodes",
        sa.Column("structural_embedding_epoch", sa.String(100), nullable=True),
    )
    op.execute(
        "UPDATE episodes SET surface_embedding_epoch = "
        f"'{CURRENT_SURFACE_EPOCH}' WHERE surface_embedding IS NOT NULL"
    )
    op.execute(
        "UPDATE episodes SET structural_embedding_epoch = "
        f"'{PRE_V07_STRUCTURAL_EPOCH}' WHERE structural_embedding IS NOT NULL"
    )
    # Retrieval filters on the current structural epoch every query.
    op.create_index(
        "ix_episodes_structural_embedding_epoch",
        "episodes",
        ["structural_embedding_epoch"],
    )


def downgrade() -> None:
    op.drop_index("ix_episodes_structural_embedding_epoch", table_name="episodes")
    op.drop_column("episodes", "structural_embedding_epoch")
    op.drop_column("episodes", "surface_embedding_epoch")

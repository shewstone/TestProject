"""Add theses.confidence, key_uncertainties, narrative_synthesis.

Three Thesis model fields had no ORM columns at all, so every write
silently discarded them (found by the T3 round-trip tests,
docs/tickets/T3-model-orm-roundtrip-tests.md).

Revision ID: 20260710_120000
Revises: 20260710_113000
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260710_120000'
down_revision: Union[str, None] = '20260710_113000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "theses",
        sa.Column("confidence", sa.String(20), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "theses",
        sa.Column("key_uncertainties", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "theses",
        sa.Column("narrative_synthesis", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("theses", "narrative_synthesis")
    op.drop_column("theses", "key_uncertainties")
    op.drop_column("theses", "confidence")

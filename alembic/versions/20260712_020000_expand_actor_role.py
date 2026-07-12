"""Allow extracted actor role descriptions longer than 100 characters.

Revision ID: 20260712_020000
Revises: 20260711_100000
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260712_020000"
down_revision: Union[str, None] = "20260711_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "actors",
        "role",
        existing_type=sa.String(length=100),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "actors",
        "role",
        existing_type=sa.Text(),
        type_=sa.String(length=100),
        existing_nullable=False,
    )

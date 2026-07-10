"""Store theses.dominant_continuation as JSON Continuation, nullable.

The Pydantic model (models.Thesis) has carried
dominant_continuation: Optional[Continuation] while the column stayed
Text NOT NULL, so writes serialized a model repr into text and reads
failed validation. Existing text values are wrapped into the
Continuation shape ({description, probability, supporting_analogs})
with probability 0.0, since the old column never stored one.

Revision ID: 20260710_113000
Revises: 20260710_100000
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260710_113000'
down_revision: Union[str, None] = '20260710_100000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "theses",
        "dominant_continuation",
        existing_type=sa.Text(),
        type_=sa.JSON(),
        nullable=True,
        postgresql_using=(
            "jsonb_build_object("
            "'description', dominant_continuation, "
            "'probability', 0.0, "
            "'supporting_analogs', 0"
            ")::json"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "theses",
        "dominant_continuation",
        existing_type=sa.JSON(),
        type_=sa.Text(),
        nullable=False,
        postgresql_using="dominant_continuation::jsonb->>'description'",
    )

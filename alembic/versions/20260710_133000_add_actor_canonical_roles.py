"""Add actors.canonical_role and role_fit_confidence (T2).

Controlled-vocabulary structural positions (extraction.roles.ActorRole)
with the classifier's fit confidence. NULL canonical_role = the mention
failed the tau_role floor and counts as vocabulary residue (Sec 10.5).
Existing rows stay NULL — they are exactly the unresolved mentions the
residue metric should see until a re-extraction pass classifies them.

Revision ID: 20260710_133000
Revises: 20260710_130000
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260710_133000'
down_revision: Union[str, None] = '20260710_130000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("actors", sa.Column("canonical_role", sa.String(60), nullable=True))
    op.add_column("actors", sa.Column("role_fit_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("actors", "role_fit_confidence")
    op.drop_column("actors", "canonical_role")

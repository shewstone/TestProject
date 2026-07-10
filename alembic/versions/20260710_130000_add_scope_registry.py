"""Add scopes table and theses.scope_registry_version (T5).

The scopes table mirrors the packaged scope registry
(narrative_engine/data/scope_registry.json) so scope ids are queryable in
SQL; ScopeRepository.sync_from_registry populates it. Rows are not seeded
here — migrations shouldn't depend on packaged data files.

Revision ID: 20260710_130000
Revises: 20260710_123000
Create Date: 2026-07-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260710_130000'
down_revision: Union[str, None] = '20260710_123000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scopes",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "parent_scope_id",
            sa.String(100),
            sa.ForeignKey("scopes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "theses",
        sa.Column("scope_registry_version", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("theses", "scope_registry_version")
    op.drop_table("scopes")

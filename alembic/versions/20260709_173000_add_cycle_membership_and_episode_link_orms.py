"""Add cycle_memberships (replacing cycle_episode_association) and is_arc_instance

Design doc Sec 4: CycleMembership needs link_status/review_status/
salience/phase_coverage/reading, none of which the bare
cycle_episode_association association table had room for. Replaces it
with a proper cycle_memberships table, migrating existing rows across
with the same defaults the ORM/Pydantic layer now uses (attested/auto).

Also adds Cycle.is_arc_instance: arc instances (Sec 2) are episodic-scale
cycles by convention, populated by the composition pass -- CycleMembership
rows targeting such a cycle are effectively COMPOSES edges.

episode_links (episode<->episode: CAUSES/PRECEDES/SAME_EVENT_AS) already
exists from the 20260709_162900 migration and needs no schema change here
-- only the ORM/repository/Pydantic-validator wiring landed in this
revision's paired code change.

Revision ID: 20260709_173000
Revises: 20260709_171500
Create Date: 2026-07-09 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260709_173000'
down_revision: Union[str, None] = '20260709_171500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cycles',
        sa.Column('is_arc_instance', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        'cycle_memberships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('episode_id', sa.UUID(), nullable=False),
        sa.Column('cycle_id', sa.UUID(), nullable=False),
        sa.Column('reading', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('salience', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('phase_coverage', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('link_status', sa.String(length=50), nullable=False, server_default='attested'),
        sa.Column('review_status', sa.String(length=50), nullable=False, server_default='auto'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cycle_id'], ['cycles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('episode_id', 'cycle_id', name='uq_cycle_membership'),
    )
    op.create_index('ix_cycle_memberships_episode', 'cycle_memberships', ['episode_id'])
    op.create_index('ix_cycle_memberships_cycle', 'cycle_memberships', ['cycle_id'])
    op.create_index('ix_cycle_memberships_link_status', 'cycle_memberships', ['link_status'])
    op.create_index('ix_cycle_memberships_review_status', 'cycle_memberships', ['review_status'])

    # Migrate existing plain memberships across with the same defaults
    # (attested/auto) before dropping the old table.
    op.execute(
        """
        INSERT INTO cycle_memberships (id, episode_id, cycle_id, salience, phase_coverage, link_status, review_status, created_at)
        SELECT gen_random_uuid(), episode_id, cycle_id, 0.5, '[]'::jsonb, 'attested', 'auto', NOW()
        FROM cycle_episode_association
        """
    )

    op.drop_table('cycle_episode_association')


def downgrade() -> None:
    op.create_table(
        'cycle_episode_association',
        sa.Column('cycle_id', sa.UUID(), nullable=False),
        sa.Column('episode_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['cycle_id'], ['cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('cycle_id', 'episode_id'),
    )
    op.execute(
        """
        INSERT INTO cycle_episode_association (cycle_id, episode_id)
        SELECT cycle_id, episode_id FROM cycle_memberships
        """
    )

    op.drop_index('ix_cycle_memberships_review_status', table_name='cycle_memberships')
    op.drop_index('ix_cycle_memberships_link_status', table_name='cycle_memberships')
    op.drop_index('ix_cycle_memberships_cycle', table_name='cycle_memberships')
    op.drop_index('ix_cycle_memberships_episode', table_name='cycle_memberships')
    op.drop_table('cycle_memberships')

    op.drop_column('cycles', 'is_arc_instance')

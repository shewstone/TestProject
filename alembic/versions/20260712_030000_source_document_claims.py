"""Prevent duplicate processing claims for the same dropped file.

Revision ID: 20260712_030000
Revises: 20260712_020000
Create Date: 2026-07-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260712_030000"
down_revision: Union[str, None] = "20260712_020000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "source_documents",
        sa.Column("claim_token", sa.UUID(), nullable=True),
    )
    op.add_column(
        "source_documents",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Collapse repeated exact ledger rows before adding the exact-pair
    # constraint. Redirect duplicate_of references so no provenance points at
    # a row removed by the cleanup.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       first_value(id) OVER (
                           PARTITION BY content_hash, filename
                           ORDER BY (status = 'completed') DESC,
                                    extraction_ran DESC,
                                    chunks_processed DESC,
                                    episodes_created DESC,
                                    created_at DESC,
                                    id
                       ) AS keep_id,
                       row_number() OVER (
                           PARTITION BY content_hash, filename
                           ORDER BY (status = 'completed') DESC,
                                    extraction_ran DESC,
                                    chunks_processed DESC,
                                    episodes_created DESC,
                                    created_at DESC,
                                    id
                       ) AS rn
                FROM source_documents
            )
            UPDATE source_documents AS document
               SET duplicate_of = ranked.keep_id
              FROM ranked
             WHERE ranked.rn > 1
               AND document.duplicate_of = ranked.id
            """
        )
    )
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY content_hash, filename
                           ORDER BY (status = 'completed') DESC,
                                    extraction_ran DESC,
                                    chunks_processed DESC,
                                    episodes_created DESC,
                                    created_at DESC,
                                    id
                       ) AS rn
                FROM source_documents
            )
            DELETE FROM source_documents AS document
             USING ranked
             WHERE document.id = ranked.id
               AND ranked.rn > 1
            """
        )
    )

    # Preserve the earliest active row for each hash and convert later active
    # collisions into visible duplicate ledger rows.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id,
                       first_value(id) OVER (
                           PARTITION BY content_hash
                           ORDER BY (status = 'completed') DESC,
                                    extraction_ran DESC,
                                    chunks_processed DESC,
                                    episodes_created DESC,
                                    created_at DESC,
                                    id
                       ) AS original_id,
                       row_number() OVER (
                           PARTITION BY content_hash
                           ORDER BY (status = 'completed') DESC,
                                    extraction_ran DESC,
                                    chunks_processed DESC,
                                    episodes_created DESC,
                                    created_at DESC,
                                    id
                       ) AS rn
                FROM source_documents
                WHERE status != 'duplicate'
            )
            UPDATE source_documents AS document
               SET status = 'duplicate',
                   duplicate_of = ranked.original_id,
                   error = COALESCE(
                       document.error,
                       'Consolidated duplicate during claim-safety migration'
                   )
              FROM ranked
             WHERE document.id = ranked.id
               AND ranked.rn > 1
            """
        )
    )

    op.create_unique_constraint(
        "uq_source_documents_hash_filename",
        "source_documents",
        ["content_hash", "filename"],
    )
    op.create_index(
        "uq_source_documents_active_hash",
        "source_documents",
        ["content_hash"],
        unique=True,
        postgresql_where=sa.text("status != 'duplicate'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_source_documents_active_hash",
        table_name="source_documents",
    )
    op.drop_constraint(
        "uq_source_documents_hash_filename",
        "source_documents",
        type_="unique",
    )
    op.drop_column("source_documents", "lease_expires_at")
    op.drop_column("source_documents", "claim_token")

"""add processing progress to documents

Revision ID: a1b2c3d4e5f6
Revises: eced291ccbe9
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6d0550c50f93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column(
            'chunks_total',
            sa.Integer(),
            nullable=False,
            server_default='0'
        )
    )
    op.add_column(
        'documents',
        sa.Column(
            'chunks_processed',
            sa.Integer(),
            nullable=False,
            server_default='0'
        )
    )


def downgrade() -> None:
    op.drop_column('documents', 'chunks_processed')
    op.drop_column('documents', 'chunks_total')

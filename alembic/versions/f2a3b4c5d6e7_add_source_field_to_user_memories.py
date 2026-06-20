"""add source_field to user_memories

Revision ID: f2a3b4c5d6e7
Revises: e1f2g3h4i5j6
Create Date: 2026-06-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2g3h4i5j6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'user_memories',
        sa.Column('source_field', sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('user_memories', 'source_field')

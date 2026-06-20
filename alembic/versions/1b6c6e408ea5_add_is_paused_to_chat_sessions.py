"""add is_paused to chat_sessions

Revision ID: 1b6c6e408ea5
Revises: cfab0c5cabb4
Create Date: 2026-06-20 13:47:25.833529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b6c6e408ea5'
down_revision: Union[str, Sequence[str], None] = 'cfab0c5cabb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'chat_sessions',
        sa.Column('is_paused', sa.Boolean, nullable=False, server_default='false')
    )


def downgrade() -> None:
    op.drop_column('chat_sessions', 'is_paused')

"""add business_type and escalation_notes to agents

Revision ID: cfab0c5cabb4
Revises: 4d7876fa9a7e
Create Date: 2026-06-20 13:16:14.678787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfab0c5cabb4'
down_revision: Union[str, Sequence[str], None] = '4d7876fa9a7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'agents',
        sa.Column('business_type', sa.String(20), nullable=False, server_default='products')
    )
    op.add_column(
        'agents',
        sa.Column('escalation_notes', sa.Text, nullable=True)
    )


def downgrade() -> None:
    op.drop_column('agents', 'escalation_notes')
    op.drop_column('agents', 'business_type')

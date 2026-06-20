"""create escalations table

Revision ID: 4d7876fa9a7e
Revises: f2a3b4c5d6e7
Create Date: 2026-06-20 12:25:37.418101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '4d7876fa9a7e'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'escalations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool_action_id', UUID(as_uuid=True), sa.ForeignKey('tool_actions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('is_resolved', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('escalations')

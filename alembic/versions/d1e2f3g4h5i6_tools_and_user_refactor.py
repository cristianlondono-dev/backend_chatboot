"""tools module + user refactor: canonical_id, user_channels, agent_tools, onboarding_step

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2026-06-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'd1e2f3g4h5i6'
down_revision: Union[str, None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Refactor users table ---
    op.drop_column('users', 'external_id')
    op.drop_column('users', 'name')
    op.drop_column('users', 'email')
    op.drop_column('users', 'phone')
    op.add_column('users', sa.Column('canonical_id', sa.String(255), nullable=False, server_default=''))
    op.add_column('users', sa.Column('user_type', sa.String(20), nullable=False, server_default='external'))
    op.create_unique_constraint('uq_users_canonical_id', 'users', ['canonical_id'])
    # Remove server_default after adding (we only needed it for the ALTER)
    op.alter_column('users', 'canonical_id', server_default=None)
    op.alter_column('users', 'user_type', server_default=None)

    # --- user_channels ---
    op.create_table(
        'user_channels',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('channel_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('channel', 'channel_id', name='uq_user_channels_channel_id'),
    )

    # --- chat_sessions: add onboarding_step ---
    op.add_column('chat_sessions', sa.Column('onboarding_step', sa.Integer, nullable=True))

    # --- agent_tools ---
    op.create_table(
        'agent_tools',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('identifier_type', sa.String(50), nullable=False),
        sa.Column('user_type', sa.String(20), nullable=False),
        sa.Column('resolver_type', sa.String(50), nullable=False, server_default='none'),
        sa.Column('resolver_config', sa.JSON, nullable=True),
        sa.Column('field_mapping', sa.JSON, nullable=True),
        sa.Column('onboarding_questions', sa.JSON, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('agent_tools')
    op.drop_column('chat_sessions', 'onboarding_step')
    op.drop_table('user_channels')
    op.drop_constraint('uq_users_canonical_id', 'users', type_='unique')
    op.drop_column('users', 'canonical_id')
    op.drop_column('users', 'user_type')
    op.add_column('users', sa.Column('external_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(50), nullable=True))

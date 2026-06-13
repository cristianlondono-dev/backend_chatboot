"""memory system v1: users, sessions, messages, memories, summaries

Revision ID: c1d2e3f4g5h6
Revises: b3c4d5e6f7a8
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector


revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('external_id', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # chat_sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    )

    # messages
    op.create_table(
        'messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('token_count', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # user_memories
    op.create_table(
        'user_memories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('memory', sa.Text, nullable=False),
        sa.Column('importance', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # user_memory_embeddings
    op.create_table(
        'user_memory_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('memory_id', UUID(as_uuid=True), sa.ForeignKey('user_memories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # conversation_summaries
    op.create_table(
        'conversation_summaries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id'), nullable=True),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # conversation_summary_embeddings
    op.create_table(
        'conversation_summary_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('summary_id', UUID(as_uuid=True), sa.ForeignKey('conversation_summaries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('conversation_summary_embeddings')
    op.drop_table('conversation_summaries')
    op.drop_table('user_memory_embeddings')
    op.drop_table('user_memories')
    op.drop_table('messages')
    op.drop_table('chat_sessions')
    op.drop_table('users')

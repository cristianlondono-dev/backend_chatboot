"""tool_actions and organization_configs tables

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3g4h5i6
Create Date: 2026-06-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, None] = 'd1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- organization_configs ---
    op.create_table(
        'organization_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'organization_id',
            UUID(as_uuid=True),
            sa.ForeignKey('organizations.id', ondelete='CASCADE'),
            nullable=False,
            unique=True
        ),
        sa.Column('openai_api_key', sa.String(255), nullable=True),
        sa.Column('storage_provider', sa.String(50), nullable=False, server_default='supabase'),
        sa.Column('storage_credentials', sa.JSON, nullable=True),
        sa.Column('storage_config', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- tool_actions ---
    op.create_table(
        'tool_actions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'agent_id',
            UUID(as_uuid=True),
            sa.ForeignKey('agents.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('parameters_schema', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('credentials', sa.JSON, nullable=True),
        sa.Column('config', sa.JSON, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('tool_actions')
    op.drop_table('organization_configs')

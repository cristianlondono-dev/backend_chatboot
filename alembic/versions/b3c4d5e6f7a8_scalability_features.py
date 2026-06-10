"""scalability features: agents, area, file_url, xlsx

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- knowledge_bases: add area ---
    op.add_column(
        'knowledge_bases',
        sa.Column('area', sa.String(100), nullable=True)
    )

    # --- documents: add file_url ---
    op.add_column(
        'documents',
        sa.Column('file_url', sa.String(2048), nullable=True)
    )

    # --- agents table ---
    op.create_table(
        'agents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'organization_id',
            UUID(as_uuid=True),
            sa.ForeignKey('organizations.id'),
            nullable=False
        ),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column(
            'visibility',
            sa.String(50),
            nullable=False,
            server_default='internal'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
    )

    # --- agent_knowledge_bases junction table ---
    op.create_table(
        'agent_knowledge_bases',
        sa.Column(
            'agent_id',
            UUID(as_uuid=True),
            sa.ForeignKey('agents.id', ondelete='CASCADE'),
            primary_key=True
        ),
        sa.Column(
            'knowledge_base_id',
            UUID(as_uuid=True),
            sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'),
            primary_key=True
        ),
        sa.Column(
            'added_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table('agent_knowledge_bases')
    op.drop_table('agents')
    op.drop_column('documents', 'file_url')
    op.drop_column('knowledge_bases', 'area')

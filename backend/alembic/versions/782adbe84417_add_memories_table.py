"""add_memories_table

Revision ID: 782adbe84417
Revises: 499b01b8a4a8
Create Date: 2026-08-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '782adbe84417'
down_revision: Union[str, Sequence[str], None] = 'c6048e566396'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if not inspector.has_table('memories'):
        op.create_table('memories',
            sa.Column('memory_id', sa.String(length=36), nullable=False),
            sa.Column('memory_type', sa.String(length=50), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('meeting_id', sa.Integer(), nullable=True),
            sa.Column('conversation_id', sa.String(length=255), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('embedding', sa.Text(), nullable=False),
            sa.Column('metadata', sa.Text(), nullable=False),
            sa.Column('importance_score', sa.Float(), nullable=False, default=0.0),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=False),
            sa.Column('access_count', sa.Integer(), nullable=False, default=0),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('memory_id')
        )
        op.create_index('ix_memories_user_id', 'memories', ['user_id'], unique=False)
        op.create_index('ix_memories_memory_type', 'memories', ['memory_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('memories')

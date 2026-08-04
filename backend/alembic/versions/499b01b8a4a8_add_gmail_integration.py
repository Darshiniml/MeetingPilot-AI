"""add_gmail_integration

Revision ID: 499b01b8a4a8
Revises: b93dae984417
Create Date: 2026-08-01 07:07:32.632941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '499b01b8a4a8'
down_revision: Union[str, Sequence[str], None] = 'b93dae984417'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Create email_logs table
    if not inspector.has_table('email_logs'):
        op.create_table('email_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=True),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )

    # 2. Add scopes column to google_calendar_tokens
    token_cols = [col['name'] for col in inspector.get_columns('google_calendar_tokens')]
    if 'scopes' not in token_cols:
        with op.batch_alter_table('google_calendar_tokens', schema=None) as batch_op:
            batch_op.add_column(sa.Column('scopes', sa.String(length=512), nullable=True))

    # 3. Add Gmail columns to meetings
    meeting_cols = [col['name'] for col in inspector.get_columns('meetings')]
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        if 'gmail_message_id' not in meeting_cols:
            batch_op.add_column(sa.Column('gmail_message_id', sa.String(length=255), nullable=True))
        if 'gmail_thread_id' not in meeting_cols:
            batch_op.add_column(sa.Column('gmail_thread_id', sa.String(length=255), nullable=True))
        if 'invitation_sent_at' not in meeting_cols:
            batch_op.add_column(sa.Column('invitation_sent_at', sa.DateTime(timezone=True), nullable=True))
        if 'invitation_status' not in meeting_cols:
            batch_op.add_column(sa.Column('invitation_status', sa.String(length=50), nullable=True))
        if 'last_email_at' not in meeting_cols:
            batch_op.add_column(sa.Column('last_email_at', sa.DateTime(timezone=True), nullable=True))

    # Reconcile transcripts index
    try:
        trans_indexes = [idx['name'] for idx in inspector.get_indexes('transcripts')]
        if 'ix_transcripts_meeting_id' not in trans_indexes:
            op.create_index('ix_transcripts_meeting_id', 'transcripts', ['meeting_id'], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('last_email_at')
        batch_op.drop_column('invitation_status')
        batch_op.drop_column('invitation_sent_at')
        batch_op.drop_column('gmail_thread_id')
        batch_op.drop_column('gmail_message_id')
        
    with op.batch_alter_table('google_calendar_tokens', schema=None) as batch_op:
        batch_op.drop_column('scopes')
        
    op.drop_table('email_logs')

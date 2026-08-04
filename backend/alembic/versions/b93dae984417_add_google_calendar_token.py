"""add_google_calendar_token

Revision ID: b93dae984417
Revises: 54546615b2c0
Create Date: 2026-08-01 06:46:51.324910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b93dae984417'
down_revision: Union[str, Sequence[str], None] = '54546615b2c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table('google_calendar_tokens'):
        op.create_table('google_calendar_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('google_email', sa.String(length=255), nullable=False),
        sa.Column('access_token', sa.String(length=1024), nullable=False),
        sa.Column('refresh_token', sa.String(length=1024), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_connected', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
        )
    
    try:
        op.drop_index('ix_transcripts_legacy_meeting_id', table_name='transcripts_legacy')
        op.drop_table('transcripts_legacy')
    except Exception:
        pass

    conn = op.get_bind()
    meetings_cols = [col['name'] for col in sa.inspect(conn).get_columns('meetings')]
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        if 'google_event_id' not in meetings_cols:
            batch_op.add_column(sa.Column('google_event_id', sa.String(length=255), nullable=True))
        if 'google_meet_link' not in meetings_cols:
            batch_op.add_column(sa.Column('google_meet_link', sa.String(length=255), nullable=True))
        if 'calendar_url' not in meetings_cols:
            batch_op.add_column(sa.Column('calendar_url', sa.String(length=1024), nullable=True))

    trans_cols = [col['name'] for col in sa.inspect(conn).get_columns('transcripts')]
    trans_constraints = [c['name'] for c in sa.inspect(conn).get_unique_constraints('transcripts')]
    with op.batch_alter_table('transcripts', schema=None) as batch_op:
        if 'segment_index' not in trans_cols:
            batch_op.add_column(sa.Column('segment_index', sa.Integer(), nullable=False, server_default='0'))
        if 'speaker_id' not in trans_cols:
            batch_op.add_column(sa.Column('speaker_id', sa.String(length=255), nullable=True))
        if 'speaker_name' not in trans_cols:
            batch_op.add_column(sa.Column('speaker_name', sa.String(length=255), nullable=True))
        if 'speaker_confidence' not in trans_cols:
            batch_op.add_column(sa.Column('speaker_confidence', sa.Float(), nullable=True))
        if 'uq_transcripts_meeting_chunk_index' in trans_constraints:
            batch_op.drop_constraint('uq_transcripts_meeting_chunk_index', type_='unique')
        if 'uq_transcripts_meeting_chunk_segment' not in trans_constraints:
            batch_op.create_unique_constraint('uq_transcripts_meeting_chunk_segment', ['meeting_id', 'chunk_index', 'segment_index'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transcripts', schema=None) as batch_op:
        batch_op.drop_constraint('uq_transcripts_meeting_chunk_segment', type_='unique')
        batch_op.drop_index('ix_transcripts_meeting_id')
        batch_op.create_unique_constraint('uq_transcripts_meeting_chunk_index', ['meeting_id', 'chunk_index'])
        batch_op.drop_column('speaker_confidence')
        batch_op.drop_column('speaker_name')
        batch_op.drop_column('speaker_id')
        batch_op.drop_column('segment_index')

    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('calendar_url')
        batch_op.drop_column('google_meet_link')
        batch_op.drop_column('google_event_id')

    op.drop_table('google_calendar_tokens')

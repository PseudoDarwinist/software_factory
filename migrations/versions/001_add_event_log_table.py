"""Add event_log table for standardized event envelope format

Revision ID: 001_event_log
Revises: 
Create Date: 2025-01-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_event_log'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('event_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('correlation_id', sa.String(length=36), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('payload', sa.Text(), nullable=False),
    sa.Column('source_agent', sa.String(length=100), nullable=True),
    sa.Column('project_id', sa.String(length=36), nullable=True),
    sa.Column('actor', sa.String(length=100), nullable=True),
    sa.Column('trace_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_log_actor'), 'event_log', ['actor'], unique=False)
    op.create_index(op.f('ix_event_log_correlation_id'), 'event_log', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_event_log_event_id'), 'event_log', ['event_id'], unique=True)
    op.create_index(op.f('ix_event_log_event_type'), 'event_log', ['event_type'], unique=False)
    op.create_index(op.f('ix_event_log_project_id'), 'event_log', ['project_id'], unique=False)
    op.create_index(op.f('ix_event_log_timestamp'), 'event_log', ['timestamp'], unique=False)
    op.create_index(op.f('ix_event_log_trace_id'), 'event_log', ['trace_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_event_log_trace_id'), table_name='event_log')
    op.drop_index(op.f('ix_event_log_timestamp'), table_name='event_log')
    op.drop_index(op.f('ix_event_log_project_id'), table_name='event_log')
    op.drop_index(op.f('ix_event_log_event_type'), table_name='event_log')
    op.drop_index(op.f('ix_event_log_event_id'), table_name='event_log')
    op.drop_index(op.f('ix_event_log_correlation_id'), table_name='event_log')
    op.drop_index(op.f('ix_event_log_actor'), table_name='event_log')
    op.drop_table('event_log')
    # ### end Alembic commands ###
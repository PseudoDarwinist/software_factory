"""Add PRDs table for storing Product Requirements Documents

Revision ID: 016_add_prds_table
Revises: 015_add_uploaded_files_columns
Create Date: 2025-01-29 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_add_prds_table'
down_revision = '015_add_uploaded_files_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Create PRDs table for storing Product Requirements Documents."""
    
    op.create_table('prds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('draft_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(10), nullable=False),
        sa.Column('md_uri', sa.Text(), nullable=True),
        sa.Column('json_uri', sa.Text(), nullable=True),
        sa.Column('sources', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes for common queries
    op.create_index('ix_prds_project_id', 'prds', ['project_id'])
    op.create_index('ix_prds_draft_id', 'prds', ['draft_id'])
    op.create_index('ix_prds_status', 'prds', ['status'])
    op.create_index('ix_prds_version', 'prds', ['version'])


def downgrade():
    """Drop PRDs table."""
    
    op.drop_index('ix_prds_version', table_name='prds')
    op.drop_index('ix_prds_status', table_name='prds')
    op.drop_index('ix_prds_draft_id', table_name='prds')
    op.drop_index('ix_prds_project_id', table_name='prds')
    op.drop_table('prds')
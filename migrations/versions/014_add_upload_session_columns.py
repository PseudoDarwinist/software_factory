"""Add missing columns to upload_sessions table

Revision ID: 014_add_upload_session_columns
Revises: 013_add_upload_tables
Create Date: 2025-01-29 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_add_upload_session_columns'
down_revision = '013_add_upload_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to upload_sessions table."""
    
    # Add missing columns to upload_sessions
    op.add_column('upload_sessions', sa.Column('ai_model_used', sa.String(50), nullable=True))
    op.add_column('upload_sessions', sa.Column('prd_preview', sa.Text(), nullable=True))
    op.add_column('upload_sessions', sa.Column('completeness_score', sa.JSON(), nullable=True))


def downgrade():
    """Remove added columns from upload_sessions table."""
    
    # Remove added columns
    op.drop_column('upload_sessions', 'completeness_score')
    op.drop_column('upload_sessions', 'prd_preview')
    op.drop_column('upload_sessions', 'ai_model_used')
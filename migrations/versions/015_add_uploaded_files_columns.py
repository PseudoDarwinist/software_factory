"""Add missing columns to uploaded_files table

Revision ID: 015_add_uploaded_files_columns
Revises: 014_add_upload_session_columns
Create Date: 2025-01-29 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_add_uploaded_files_columns'
down_revision = '014_add_upload_session_columns'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to uploaded_files table."""
    
    # Add only the missing columns to uploaded_files
    op.add_column('uploaded_files', sa.Column('page_count', sa.Integer(), nullable=True))
    op.add_column('uploaded_files', sa.Column('source_id', sa.String(10), nullable=True))


def downgrade():
    """Remove added columns from uploaded_files table."""
    
    # Remove added columns
    op.drop_column('uploaded_files', 'source_id')
    op.drop_column('uploaded_files', 'page_count')
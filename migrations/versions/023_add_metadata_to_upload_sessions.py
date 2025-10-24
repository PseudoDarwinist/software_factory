"""Add metadata field to upload_sessions table

Revision ID: 023_add_metadata
Revises: 022_add_related_idea_field
Create Date: 2025-01-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '023_add_metadata'
down_revision = '022_add_related_idea_field'
branch_labels = None
depends_on = None


def upgrade():
    # Add session_metadata column to upload_sessions table
    op.add_column('upload_sessions', sa.Column('session_metadata', postgresql.JSON(), nullable=True))


def downgrade():
    # Remove session_metadata column from upload_sessions table
    op.drop_column('upload_sessions', 'session_metadata')
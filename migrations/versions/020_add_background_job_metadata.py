"""Add metadata column to background_job table

Revision ID: 020_add_bg_job_metadata
Revises: 019_add_adi_knowledge_embeddings
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '020_add_bg_job_metadata'
down_revision = '019_add_adi_knowledge_embeddings'
branch_labels = None
depends_on = None


def upgrade():
    # Add metadata column to background_job table
    op.add_column('background_job', sa.Column('metadata', sa.JSON(), nullable=True))


def downgrade():
    # Remove metadata column
    op.drop_column('background_job', 'metadata')
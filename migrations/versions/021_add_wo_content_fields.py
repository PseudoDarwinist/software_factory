"""Add content fields for work order tabs (description, blueprint, prd)

Revision ID: 021_add_wo_content_fields
Revises: 020_add_bg_job_metadata
Create Date: 2025-01-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021_add_wo_content_fields'
down_revision = '020_add_bg_job_metadata'
branch_labels = None
depends_on = None


def upgrade():
    # Add new JSON columns for work order tab content
    op.add_column('task', sa.Column('description_content', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('task', sa.Column('blueprint_content', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('task', sa.Column('prd_content', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove the added columns
    op.drop_column('task', 'prd_content')
    op.drop_column('task', 'blueprint_content')
    op.drop_column('task', 'description_content')
"""Add related_idea field to task table

Revision ID: 022_add_related_idea_field
Revises: 021_add_wo_content_fields
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '022_add_related_idea_field'
down_revision = '021_add_wo_content_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Add related_idea field to task table
    op.add_column('task', sa.Column('related_idea', sa.String(200), nullable=True))

def downgrade():
    # Remove related_idea field from task table
    op.drop_column('task', 'related_idea')
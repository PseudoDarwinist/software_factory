"""Add github_token field to mission_control_project table

Revision ID: 010_add_github_token_to_projects
Revises: 009_add_task_intelligence_fields
Create Date: 2025-01-24 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_add_github_token_to_projects'
down_revision = '009_add_task_intelligence_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add github_token field to mission_control_project table
    # Make it nullable to maintain backward compatibility
    op.add_column('mission_control_project', sa.Column('github_token', sa.String(length=255), nullable=True))


def downgrade():
    # Remove github_token field
    op.drop_column('mission_control_project', 'github_token')
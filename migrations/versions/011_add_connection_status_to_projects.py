"""Add connection status to mission control projects

Revision ID: 011_conn_status_projects
Revises: 010_add_github_token_to_projects
Create Date: 2025-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_conn_status_projects'
down_revision = '010_add_github_token_to_projects'
branch_labels = None
depends_on = None


def upgrade():
    # Add connection_status column to mission_control_project table
    op.add_column('mission_control_project', sa.Column('connection_status', sa.String(500), nullable=True))


def downgrade():
    # Remove connection_status column from mission_control_project table
    op.drop_column('mission_control_project', 'connection_status')
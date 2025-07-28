"""Add pr_number field to task table

Revision ID: 012_add_pr_number_field
Revises: 011_conn_status_projects
Create Date: 2025-01-27 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012_add_pr_number_field'
down_revision = '011_conn_status_projects'
branch_labels = None
depends_on = None


def upgrade():
    """Add pr_number field to task table."""
    op.add_column('task', sa.Column('pr_number', sa.Integer(), nullable=True))


def downgrade():
    """Remove pr_number field from task table."""
    op.drop_column('task', 'pr_number')
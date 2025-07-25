"""Add updated_at field to background_job table

Revision ID: 007_add_background_job_updated_at
Revises: 006_add_task_table
Create Date: 2025-07-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '007_add_background_job_updated_at'
down_revision = '006_add_task_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add updated_at column to background_job table"""
    # Add the updated_at column
    op.add_column('background_job', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Update existing records to have current timestamp
    op.execute(f"UPDATE background_job SET updated_at = '{datetime.utcnow().isoformat()}' WHERE updated_at IS NULL")
    
    # Make the column non-nullable
    op.alter_column('background_job', 'updated_at', nullable=False)


def downgrade():
    """Remove updated_at column from background_job table"""
    op.drop_column('background_job', 'updated_at')
"""Add task execution fields

Revision ID: 008_add_task_execution_fields
Revises: 007_add_background_job_updated_at
Create Date: 2025-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_add_task_execution_fields'
down_revision = '007_add_background_job_updated_at'
branch_labels = None
depends_on = None


def upgrade():
    # Update TaskStatus enum to include new values
    op.execute("ALTER TYPE taskstatus RENAME TO taskstatus_old")
    op.execute("CREATE TYPE taskstatus AS ENUM ('ready', 'running', 'review', 'done', 'failed')")
    op.execute("ALTER TABLE task ALTER COLUMN status TYPE taskstatus USING status::text::taskstatus")
    op.execute("DROP TYPE taskstatus_old")
    
    # Add new task execution fields
    op.add_column('task', sa.Column('agent', sa.String(length=100), nullable=True))
    op.add_column('task', sa.Column('branch_name', sa.String(length=200), nullable=True))
    op.add_column('task', sa.Column('repo_url', sa.String(length=500), nullable=True))
    op.add_column('task', sa.Column('progress_messages', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('task', sa.Column('touched_files', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('task', sa.Column('error', sa.Text(), nullable=True))


def downgrade():
    # Remove new task execution fields
    op.drop_column('task', 'error')
    op.drop_column('task', 'touched_files')
    op.drop_column('task', 'progress_messages')
    op.drop_column('task', 'repo_url')
    op.drop_column('task', 'branch_name')
    op.drop_column('task', 'agent')
    
    # Revert TaskStatus enum to old values
    op.execute("ALTER TYPE taskstatus RENAME TO taskstatus_old")
    op.execute("CREATE TYPE taskstatus AS ENUM ('ready', 'in_progress', 'done', 'blocked')")
    op.execute("ALTER TABLE task ALTER COLUMN status TYPE taskstatus USING "
               "CASE "
               "WHEN status::text = 'running' THEN 'in_progress'::taskstatus "
               "WHEN status::text = 'review' THEN 'done'::taskstatus "
               "WHEN status::text = 'failed' THEN 'blocked'::taskstatus "
               "ELSE status::text::taskstatus "
               "END")
    op.execute("DROP TYPE taskstatus_old")
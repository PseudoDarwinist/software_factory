"""Add task intelligence fields for AI suggestions and reasoning

Revision ID: 009_add_task_intelligence_fields
Revises: 008_add_task_execution_fields
Create Date: 2025-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_add_task_intelligence_fields'
down_revision = '008_add_task_execution_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for AI suggestions and reasoning
    op.add_column('task', sa.Column('assignment_reasoning', sa.Text(), nullable=True))
    op.add_column('task', sa.Column('suggested_agent', sa.String(length=50), nullable=True))
    op.add_column('task', sa.Column('agent_reasoning', sa.Text(), nullable=True))
    op.add_column('task', sa.Column('effort_reasoning', sa.Text(), nullable=True))
    op.add_column('task', sa.Column('likely_touches', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('task', sa.Column('goal_line', sa.String(length=200), nullable=True))


def downgrade():
    # Remove the added columns
    op.drop_column('task', 'goal_line')
    op.drop_column('task', 'likely_touches')
    op.drop_column('task', 'effort_reasoning')
    op.drop_column('task', 'agent_reasoning')
    op.drop_column('task', 'suggested_agent')
    op.drop_column('task', 'assignment_reasoning')
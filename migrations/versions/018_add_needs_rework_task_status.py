"""Add needs_rework task status

Revision ID: 018_add_needs_rework_task_status
Revises: 017_add_idea_specific_prd_fields
Create Date: 2025-02-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018_add_needs_rework_task_status'
down_revision = '017_add_idea_specific_prd_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new enum value to the existing taskstatus enum
    op.execute("ALTER TYPE taskstatus ADD VALUE 'needs_rework'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum value in place
    pass
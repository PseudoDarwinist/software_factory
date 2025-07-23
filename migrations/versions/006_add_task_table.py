"""Add task table for Planner Agent

Revision ID: 006
Revises: 005
Create Date: 2025-01-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Add task table for storing parsed tasks from specifications."""
    
    # Create task status enum
    task_status_enum = postgresql.ENUM(
        'ready', 'in_progress', 'done', 'blocked',
        name='taskstatus',
        create_type=False
    )
    task_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create task priority enum
    task_priority_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'critical',
        name='taskpriority',
        create_type=False
    )
    task_priority_enum.create(op.get_bind(), checkfirst=True)
    
    # Create task table
    op.create_table(
        'task',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('spec_id', sa.String(100), nullable=False, index=True),
        sa.Column('project_id', sa.String(100), nullable=False, index=True),
        
        # Task content
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('task_number', sa.String(20)),
        sa.Column('parent_task_id', sa.String(100)),
        
        # Task metadata
        sa.Column('status', task_status_enum, nullable=False, default='ready'),
        sa.Column('priority', task_priority_enum, nullable=False, default='medium'),
        sa.Column('effort_estimate_hours', sa.Float),
        
        # Assignment and ownership
        sa.Column('suggested_owner', sa.String(100)),
        sa.Column('assigned_to', sa.String(100)),
        sa.Column('assignment_confidence', sa.Float),
        
        # Requirements traceability
        sa.Column('requirements_refs', sa.JSON),
        
        # Dependencies and relationships
        sa.Column('depends_on', sa.JSON),
        sa.Column('blocks', sa.JSON),
        
        # Context and relationships
        sa.Column('related_files', sa.JSON),
        sa.Column('related_components', sa.JSON),
        
        # Tracking fields
        sa.Column('created_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('updated_by', sa.String(100)),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now()),
        
        # Task execution tracking
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('started_by', sa.String(100)),
        sa.Column('completed_by', sa.String(100)),
        
        # Build integration
        sa.Column('pr_url', sa.String(500)),
        sa.Column('build_status', sa.String(50))
    )
    
    # Create indexes
    op.create_index('idx_spec_project', 'task', ['spec_id', 'project_id'])
    op.create_index('idx_status_priority', 'task', ['status', 'priority'])
    op.create_index('idx_assigned_status', 'task', ['assigned_to', 'status'])


def downgrade():
    """Remove task table and related enums."""
    
    # Drop indexes
    op.drop_index('idx_assigned_status', 'task')
    op.drop_index('idx_status_priority', 'task')
    op.drop_index('idx_spec_project', 'task')
    
    # Drop table
    op.drop_table('task')
    
    # Drop enums
    task_priority_enum = postgresql.ENUM(name='taskpriority')
    task_priority_enum.drop(op.get_bind(), checkfirst=True)
    
    task_status_enum = postgresql.ENUM(name='taskstatus')
    task_status_enum.drop(op.get_bind(), checkfirst=True)
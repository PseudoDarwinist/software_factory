"""Add specification_artifact table

Revision ID: 002
Revises: 001
Create Date: 2025-07-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_event_log'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    artifact_type_enum = postgresql.ENUM('requirements', 'design', 'tasks', name='artifacttype')
    artifact_type_enum.create(op.get_bind())
    
    artifact_status_enum = postgresql.ENUM('ai_draft', 'human_reviewed', 'frozen', name='artifactstatus')
    artifact_status_enum.create(op.get_bind())
    
    # Create specification_artifact table
    op.create_table('specification_artifact',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('spec_id', sa.String(length=100), nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('artifact_type', artifact_type_enum, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', artifact_status_enum, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('ai_generated', sa.Boolean(), nullable=False),
        sa.Column('ai_model_used', sa.String(length=100), nullable=True),
        sa.Column('context_sources', sa.JSON(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('notion_page_id', sa.String(length=100), nullable=True),
        sa.Column('notion_synced_at', sa.DateTime(), nullable=True),
        sa.Column('notion_sync_status', sa.String(length=50), nullable=True),
        # Foreign key omitted due to string IDs in MissionControlProject
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('spec_id', 'artifact_type', name='uq_spec_artifact')
    )
    
    # Create indexes
    op.create_index('idx_project_spec', 'specification_artifact', ['project_id', 'spec_id'])
    op.create_index('idx_status_type', 'specification_artifact', ['status', 'artifact_type'])
    op.create_index(op.f('ix_specification_artifact_project_id'), 'specification_artifact', ['project_id'])
    op.create_index(op.f('ix_specification_artifact_spec_id'), 'specification_artifact', ['spec_id'])


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_specification_artifact_spec_id'), 'specification_artifact')
    op.drop_index(op.f('ix_specification_artifact_project_id'), 'specification_artifact')
    op.drop_index('idx_status_type', 'specification_artifact')
    op.drop_index('idx_project_spec', 'specification_artifact')
    
    # Drop table
    op.drop_table('specification_artifact')
    
    # Drop enum types
    artifact_status_enum = postgresql.ENUM('ai_draft', 'human_reviewed', 'frozen', name='artifactstatus')
    artifact_status_enum.drop(op.get_bind())
    
    artifact_type_enum = postgresql.ENUM('requirements', 'design', 'tasks', name='artifacttype')
    artifact_type_enum.drop(op.get_bind())
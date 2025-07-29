"""Add upload_sessions and uploaded_files tables

Revision ID: 013_add_upload_tables
Revises: 012_add_pr_number_field
Create Date: 2025-01-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013_add_upload_tables'
down_revision = '012_add_pr_number_field'
branch_labels = None
depends_on = None


def upgrade():
    """Create upload_sessions and uploaded_files tables."""
    
    # Create upload_sessions table
    op.create_table('upload_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('combined_content', sa.Text(), nullable=True),
        sa.Column('ai_analysis', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create uploaded_files table
    op.create_table('uploaded_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('processing_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['upload_sessions.id'], ondelete='CASCADE')
    )
    
    # Add indexes for performance
    op.create_index('ix_upload_sessions_project_id', 'upload_sessions', ['project_id'])
    op.create_index('ix_upload_sessions_status', 'upload_sessions', ['status'])
    op.create_index('ix_uploaded_files_session_id', 'uploaded_files', ['session_id'])
    op.create_index('ix_uploaded_files_processing_status', 'uploaded_files', ['processing_status'])
    
    # Add foreign key constraint to mission_control_project
    op.create_foreign_key(
        'fk_upload_sessions_project_id',
        'upload_sessions', 'mission_control_project',
        ['project_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    """Drop upload_sessions and uploaded_files tables."""
    
    # Drop foreign key constraints first
    op.drop_constraint('fk_upload_sessions_project_id', 'upload_sessions', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_uploaded_files_processing_status', 'uploaded_files')
    op.drop_index('ix_uploaded_files_session_id', 'uploaded_files')
    op.drop_index('ix_upload_sessions_status', 'upload_sessions')
    op.drop_index('ix_upload_sessions_project_id', 'upload_sessions')
    
    # Drop tables
    op.drop_table('uploaded_files')
    op.drop_table('upload_sessions')
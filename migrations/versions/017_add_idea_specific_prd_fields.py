"""Add idea-specific PRD fields

Revision ID: add_idea_prd_fields
Revises: previous_migration
Create Date: 2025-01-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_add_idea_specific_prd_fields'
down_revision = '016_add_prds_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to support idea-specific PRDs"""
    
    # Add feed_item_id column for 1:1 relationship with ideas
    op.add_column('prds', sa.Column('feed_item_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add parent_version_id for PRD version history
    op.add_column('prds', sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add source_files column for detailed file metadata
    op.add_column('prds', sa.Column('source_files', sa.JSON(), nullable=True))
    
    # Create indexes for better query performance
    op.create_index('ix_prds_feed_item_id', 'prds', ['feed_item_id'])
    op.create_index('ix_prds_parent_version_id', 'prds', ['parent_version_id'])
    
    # Create foreign key constraint for parent_version_id (self-referencing)
    op.create_foreign_key(
        'fk_prds_parent_version_id',
        'prds', 'prds',
        ['parent_version_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    """Remove idea-specific PRD fields"""
    
    # Drop foreign key constraint
    op.drop_constraint('fk_prds_parent_version_id', 'prds', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_prds_parent_version_id', 'prds')
    op.drop_index('ix_prds_feed_item_id', 'prds')
    
    # Drop columns
    op.drop_column('prds', 'source_files')
    op.drop_column('prds', 'parent_version_id')
    op.drop_column('prds', 'feed_item_id')
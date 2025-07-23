"""Fix specification_artifact project_id to use string

Revision ID: 005
Revises: 004
Create Date: 2025-07-21 07:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the foreign key constraint
    op.drop_constraint('specification_artifact_project_id_fkey', 'specification_artifact', type_='foreignkey')
    
    # Change project_id column from INTEGER to VARCHAR(100)
    op.alter_column('specification_artifact', 'project_id',
                    existing_type=sa.INTEGER(),
                    type_=sa.String(length=100),
                    existing_nullable=False)


def downgrade():
    # Change project_id column back to INTEGER
    op.alter_column('specification_artifact', 'project_id',
                    existing_type=sa.String(length=100),
                    type_=sa.INTEGER(),
                    existing_nullable=False)
    
    # Re-add the foreign key constraint
    op.create_foreign_key('specification_artifact_project_id_fkey', 'specification_artifact', 'project', ['project_id'], ['id'])
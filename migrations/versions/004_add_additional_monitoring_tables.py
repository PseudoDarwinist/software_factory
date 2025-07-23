"""Add additional monitoring tables

Revision ID: 004
Revises: 003
Create Date: 2025-01-20 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Create alert_history table
    op.create_table('alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.String(length=100), nullable=False),
        sa.Column('alert_type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), nullable=False),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for alert_history
    op.create_index('ix_alert_history_alert_id', 'alert_history', ['alert_id'])
    op.create_index('ix_alert_history_timestamp', 'alert_history', ['timestamp'])
    op.create_index('idx_alert_type_time', 'alert_history', ['alert_type', 'timestamp'])
    op.create_index('idx_alert_source_time', 'alert_history', ['source', 'timestamp'])
    op.create_index('idx_alert_status', 'alert_history', ['acknowledged', 'resolved'])
    
    # Create integration_status table
    op.create_table('integration_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('integration_name', sa.String(length=100), nullable=False),
        sa.Column('integration_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('last_success', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('average_response_time', sa.Float(), nullable=True),
        sa.Column('api_usage_count', sa.Integer(), nullable=True),
        sa.Column('rate_limit_remaining', sa.Integer(), nullable=True),
        sa.Column('rate_limit_reset', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for integration_status
    op.create_index('ix_integration_status_integration_name', 'integration_status', ['integration_name'])
    op.create_index('ix_integration_status_timestamp', 'integration_status', ['timestamp'])
    op.create_index('idx_integration_type_time', 'integration_status', ['integration_type', 'timestamp'])
    op.create_index('idx_integration_status', 'integration_status', ['status'])
    
    # Create dashboard_config table
    op.create_table('dashboard_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_type', sa.String(length=50), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    
    # Create indexes for dashboard_config
    op.create_index('ix_dashboard_config_config_key', 'dashboard_config', ['config_key'])


def downgrade():
    # Drop dashboard_config table
    op.drop_index('ix_dashboard_config_config_key', table_name='dashboard_config')
    op.drop_table('dashboard_config')
    
    # Drop integration_status table
    op.drop_index('idx_integration_status', table_name='integration_status')
    op.drop_index('idx_integration_type_time', table_name='integration_status')
    op.drop_index('ix_integration_status_timestamp', table_name='integration_status')
    op.drop_index('ix_integration_status_integration_name', table_name='integration_status')
    op.drop_table('integration_status')
    
    # Drop alert_history table
    op.drop_index('idx_alert_status', table_name='alert_history')
    op.drop_index('idx_alert_source_time', table_name='alert_history')
    op.drop_index('idx_alert_type_time', table_name='alert_history')
    op.drop_index('ix_alert_history_timestamp', table_name='alert_history')
    op.drop_index('ix_alert_history_alert_id', table_name='alert_history')
    op.drop_table('alert_history')
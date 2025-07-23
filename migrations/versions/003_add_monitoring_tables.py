"""Add monitoring tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create monitoring_metrics table
    op.create_table('monitoring_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(length=100), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for monitoring_metrics
    op.create_index('idx_metrics_type_name_time', 'monitoring_metrics', ['metric_type', 'metric_name', 'timestamp'])
    op.create_index('idx_metrics_source_time', 'monitoring_metrics', ['source_id', 'timestamp'])
    op.create_index('ix_monitoring_metrics_metric_type', 'monitoring_metrics', ['metric_type'])
    op.create_index('ix_monitoring_metrics_metric_name', 'monitoring_metrics', ['metric_name'])
    op.create_index('ix_monitoring_metrics_source_id', 'monitoring_metrics', ['source_id'])
    op.create_index('ix_monitoring_metrics_timestamp', 'monitoring_metrics', ['timestamp'])
    
    # Create agent_status table
    op.create_table('agent_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('heartbeat_status', sa.String(length=20), nullable=False),
        sa.Column('events_processed', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('average_processing_time', sa.Float(), nullable=True),
        sa.Column('current_load', sa.Integer(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for agent_status
    op.create_index('ix_agent_status_agent_id', 'agent_status', ['agent_id'])
    
    # Create system_health table
    op.create_table('system_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('components', sa.Text(), nullable=True),
        sa.Column('resources', sa.Text(), nullable=True),
        sa.Column('performance', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for system_health
    op.create_index('ix_system_health_timestamp', 'system_health', ['timestamp'])


def downgrade():
    # Drop system_health table
    op.drop_index('ix_system_health_timestamp', table_name='system_health')
    op.drop_table('system_health')
    
    # Drop agent_status table
    op.drop_index('ix_agent_status_agent_id', table_name='agent_status')
    op.drop_table('agent_status')
    
    # Drop monitoring_metrics table
    op.drop_index('ix_monitoring_metrics_timestamp', table_name='monitoring_metrics')
    op.drop_index('ix_monitoring_metrics_source_id', table_name='monitoring_metrics')
    op.drop_index('ix_monitoring_metrics_metric_name', table_name='monitoring_metrics')
    op.drop_index('ix_monitoring_metrics_metric_type', table_name='monitoring_metrics')
    op.drop_index('idx_metrics_source_time', table_name='monitoring_metrics')
    op.drop_index('idx_metrics_type_name_time', table_name='monitoring_metrics')
    op.drop_table('monitoring_metrics')
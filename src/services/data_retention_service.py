"""
Data retention and cleanup service for monitoring data.

This service implements data retention policies including:
- Down-sampling high-resolution metrics after 7 days
- Purging old data after 30 days
- Cleanup of old alert history
- Optimization of database storage
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import text, func

from ..models.base import db
from ..models.monitoring_metrics import (
    MonitoringMetrics, 
    AgentStatus, 
    SystemHealth, 
    AlertHistory, 
    IntegrationStatus
)

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Service for managing data retention and cleanup policies."""
    
    def __init__(self):
        self.logger = logger
    
    def run_nightly_cleanup(self) -> Dict[str, Any]:
        """
        Run the nightly cleanup process.
        
        This includes:
        1. Down-sampling metrics older than 7 days
        2. Purging data older than 30 days
        3. Cleaning up old alert history
        4. Optimizing database storage
        
        Returns:
            Dict with cleanup statistics
        """
        self.logger.info("Starting nightly data retention cleanup")
        
        results = {
            'start_time': datetime.utcnow().isoformat(),
            'metrics_downsampled': 0,
            'metrics_purged': 0,
            'alerts_purged': 0,
            'system_health_purged': 0,
            'integration_status_purged': 0,
            'errors': []
        }
        
        try:
            # 1. Down-sample metrics older than 7 days
            results['metrics_downsampled'] = self._downsample_metrics()
            
            # 2. Purge old data
            results['metrics_purged'] = self._purge_old_metrics()
            results['alerts_purged'] = self._purge_old_alerts()
            results['system_health_purged'] = self._purge_old_system_health()
            results['integration_status_purged'] = self._purge_old_integration_status()
            
            # 3. Optimize database
            self._optimize_database()
            
            results['end_time'] = datetime.utcnow().isoformat()
            results['success'] = True
            
            self.logger.info(f"Nightly cleanup completed successfully: {results}")
            
        except Exception as e:
            error_msg = f"Error during nightly cleanup: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['success'] = False
            results['end_time'] = datetime.utcnow().isoformat()
        
        return results
    
    def _downsample_metrics(self, days_old: int = 7) -> int:
        """
        Down-sample high-resolution metrics to hourly averages.
        
        Args:
            days_old: Age in days after which to down-sample
            
        Returns:
            Number of metrics processed
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            # Get metrics older than cutoff that haven't been down-sampled
            old_metrics = db.session.query(MonitoringMetrics).filter(
                MonitoringMetrics.timestamp < cutoff_date,
                ~MonitoringMetrics.meta_data.like('%"downsampled": true%')
            ).all()
            
            if not old_metrics:
                return 0
            
            # Group metrics by type, name, source, and hour
            hourly_groups = {}
            
            for metric in old_metrics:
                # Round timestamp to hour
                hour_key = metric.timestamp.replace(minute=0, second=0, microsecond=0)
                group_key = (
                    metric.metric_type,
                    metric.metric_name,
                    metric.source_id,
                    hour_key
                )
                
                if group_key not in hourly_groups:
                    hourly_groups[group_key] = []
                
                hourly_groups[group_key].append(metric)
            
            downsampled_count = 0
            
            # Create hourly averages
            for group_key, metrics in hourly_groups.items():
                metric_type, metric_name, source_id, hour_timestamp = group_key
                
                # Calculate average value
                avg_value = sum(m.value for m in metrics) / len(metrics)
                
                # Create down-sampled metric
                downsampled_metric = MonitoringMetrics(
                    metric_type=metric_type,
                    metric_name=metric_name,
                    source_id=source_id,
                    timestamp=hour_timestamp,
                    value=avg_value,
                    meta_data='{"downsampled": true, "original_count": ' + str(len(metrics)) + '}'
                )
                
                db.session.add(downsampled_metric)
                
                # Mark original metrics for deletion
                for metric in metrics:
                    db.session.delete(metric)
                
                downsampled_count += len(metrics)
            
            db.session.commit()
            
            self.logger.info(f"Down-sampled {downsampled_count} metrics into {len(hourly_groups)} hourly averages")
            return downsampled_count
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error down-sampling metrics: {str(e)}", exc_info=True)
            raise
    
    def _purge_old_metrics(self, days_old: int = 30) -> int:
        """
        Purge metrics older than specified days.
        
        Args:
            days_old: Age in days after which to purge
            
        Returns:
            Number of metrics purged
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            # Count metrics to be deleted
            count = db.session.query(MonitoringMetrics).filter(
                MonitoringMetrics.timestamp < cutoff_date
            ).count()
            
            if count == 0:
                return 0
            
            # Delete old metrics in batches to avoid locking
            batch_size = 1000
            total_deleted = 0
            
            while True:
                batch = db.session.query(MonitoringMetrics).filter(
                    MonitoringMetrics.timestamp < cutoff_date
                ).limit(batch_size).all()
                
                if not batch:
                    break
                
                for metric in batch:
                    db.session.delete(metric)
                
                db.session.commit()
                total_deleted += len(batch)
                
                self.logger.debug(f"Deleted batch of {len(batch)} metrics, total: {total_deleted}")
            
            self.logger.info(f"Purged {total_deleted} old metrics")
            return total_deleted
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error purging old metrics: {str(e)}", exc_info=True)
            raise
    
    def _purge_old_alerts(self, days_old: int = 90) -> int:
        """
        Purge resolved alerts older than specified days.
        
        Args:
            days_old: Age in days after which to purge resolved alerts
            
        Returns:
            Number of alerts purged
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            # Only purge resolved alerts
            count = db.session.query(AlertHistory).filter(
                AlertHistory.timestamp < cutoff_date,
                AlertHistory.resolved == True
            ).count()
            
            if count == 0:
                return 0
            
            # Delete old resolved alerts
            deleted = db.session.query(AlertHistory).filter(
                AlertHistory.timestamp < cutoff_date,
                AlertHistory.resolved == True
            ).delete()
            
            db.session.commit()
            
            self.logger.info(f"Purged {deleted} old resolved alerts")
            return deleted
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error purging old alerts: {str(e)}", exc_info=True)
            raise
    
    def _purge_old_system_health(self, days_old: int = 30) -> int:
        """
        Purge system health records older than specified days.
        
        Args:
            days_old: Age in days after which to purge
            
        Returns:
            Number of records purged
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            count = db.session.query(SystemHealth).filter(
                SystemHealth.timestamp < cutoff_date
            ).count()
            
            if count == 0:
                return 0
            
            deleted = db.session.query(SystemHealth).filter(
                SystemHealth.timestamp < cutoff_date
            ).delete()
            
            db.session.commit()
            
            self.logger.info(f"Purged {deleted} old system health records")
            return deleted
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error purging old system health records: {str(e)}", exc_info=True)
            raise
    
    def _purge_old_integration_status(self, days_old: int = 30) -> int:
        """
        Purge integration status records older than specified days.
        Keep only the latest record for each integration.
        
        Args:
            days_old: Age in days after which to purge
            
        Returns:
            Number of records purged
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            # Get the latest record for each integration
            latest_records = db.session.query(
                IntegrationStatus.integration_name,
                func.max(IntegrationStatus.timestamp).label('latest_timestamp')
            ).group_by(IntegrationStatus.integration_name).all()
            
            # Build list of IDs to keep
            ids_to_keep = []
            for integration_name, latest_timestamp in latest_records:
                latest_record = db.session.query(IntegrationStatus).filter(
                    IntegrationStatus.integration_name == integration_name,
                    IntegrationStatus.timestamp == latest_timestamp
                ).first()
                
                if latest_record:
                    ids_to_keep.append(latest_record.id)
            
            # Delete old records except the latest ones
            deleted = db.session.query(IntegrationStatus).filter(
                IntegrationStatus.timestamp < cutoff_date,
                ~IntegrationStatus.id.in_(ids_to_keep)
            ).delete(synchronize_session=False)
            
            db.session.commit()
            
            self.logger.info(f"Purged {deleted} old integration status records")
            return deleted
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error purging old integration status records: {str(e)}", exc_info=True)
            raise
    
    def _optimize_database(self):
        """
        Optimize database performance after cleanup.
        
        This includes:
        - Analyzing tables for query optimization
        - Updating statistics
        - Reclaiming space
        """
        try:
            # PostgreSQL-specific optimization
            tables = [
                'monitoring_metrics',
                'agent_status', 
                'system_health',
                'alert_history',
                'integration_status',
                'dashboard_config'
            ]
            
            for table in tables:
                # Analyze table for query optimization
                db.session.execute(text(f'ANALYZE {table}'))
            
            db.session.commit()
            
            self.logger.info("Database optimization completed")
            
        except Exception as e:
            self.logger.error(f"Error optimizing database: {str(e)}", exc_info=True)
            # Don't raise here as this is not critical
    
    def get_retention_stats(self) -> Dict[str, Any]:
        """
        Get statistics about data retention and storage usage.
        
        Returns:
            Dict with retention statistics
        """
        try:
            stats = {
                'timestamp': datetime.utcnow().isoformat(),
                'tables': {}
            }
            
            # Get counts for each table
            tables = [
                ('monitoring_metrics', MonitoringMetrics),
                ('agent_status', AgentStatus),
                ('system_health', SystemHealth),
                ('alert_history', AlertHistory),
                ('integration_status', IntegrationStatus)
            ]
            
            for table_name, model_class in tables:
                total_count = db.session.query(model_class).count()
                
                # Get age distribution
                now = datetime.utcnow()
                day_ago = now - timedelta(days=1)
                week_ago = now - timedelta(days=7)
                month_ago = now - timedelta(days=30)
                
                if hasattr(model_class, 'timestamp'):
                    recent_count = db.session.query(model_class).filter(
                        model_class.timestamp >= day_ago
                    ).count()
                    
                    week_count = db.session.query(model_class).filter(
                        model_class.timestamp >= week_ago
                    ).count()
                    
                    month_count = db.session.query(model_class).filter(
                        model_class.timestamp >= month_ago
                    ).count()
                else:
                    # Use created_at for tables without timestamp
                    recent_count = db.session.query(model_class).filter(
                        model_class.created_at >= day_ago
                    ).count()
                    
                    week_count = db.session.query(model_class).filter(
                        model_class.created_at >= week_ago
                    ).count()
                    
                    month_count = db.session.query(model_class).filter(
                        model_class.created_at >= month_ago
                    ).count()
                
                stats['tables'][table_name] = {
                    'total_records': total_count,
                    'last_24h': recent_count,
                    'last_7d': week_count,
                    'last_30d': month_count,
                    'older_than_30d': total_count - month_count
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting retention stats: {str(e)}", exc_info=True)
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }


# Global instance
data_retention_service = DataRetentionService()
"""
Decision Log Cleanup Service

Handles automatic cleanup of expired decision logs and maintenance tasks.
"""

from datetime import datetime, timedelta
import logging
from typing import Dict, Any

try:
    from ..models.decision_log import DecisionLog
    from ...models.base import db
    from ...services.background import get_job_manager, JobContext, JobResult
    from ...models.background_job import BackgroundJob
except ImportError:
    try:
        from src.adi.models.decision_log import DecisionLog
        from src.models.base import db
        from src.services.background import get_job_manager, JobContext, JobResult
        from src.models.background_job import BackgroundJob
    except ImportError:
        from adi.models.decision_log import DecisionLog
        from models.base import db
        from services.background import get_job_manager, JobContext, JobResult
        from models.background_job import BackgroundJob

logger = logging.getLogger(__name__)


class DecisionLogCleanupService:
    """Service for managing decision log cleanup and maintenance."""
    
    # Job type for cleanup tasks
    JOB_TYPE_CLEANUP = 'adi_decision_log_cleanup'
    
    def __init__(self):
        self.job_manager = get_job_manager()
        
        # Register cleanup job handler
        if hasattr(self.job_manager, 'job_handlers'):
            self.job_manager.job_handlers[self.JOB_TYPE_CLEANUP] = self._handle_cleanup_job
    
    def schedule_cleanup_job(self, max_age_days: int = 60, batch_size: int = 1000) -> int:
        """
        Schedule a cleanup job to remove expired decision logs.
        
        Args:
            max_age_days: Maximum age of logs to keep (default: 60 days)
            batch_size: Number of logs to process in each batch (default: 1000)
            
        Returns:
            Job ID of the scheduled cleanup job
        """
        logger.info(f"Scheduling decision log cleanup job (max_age_days={max_age_days}, batch_size={batch_size})")
        
        job_id = self.job_manager.submit_job(
            job_type=self.JOB_TYPE_CLEANUP,
            project_id=None,  # System-wide cleanup
            max_age_days=max_age_days,
            batch_size=batch_size
        )
        
        logger.info(f"Cleanup job scheduled with ID: {job_id}")
        return job_id
    
    def get_cleanup_stats(self, max_age_days: int = 60) -> Dict[str, Any]:
        """
        Get statistics about logs that would be cleaned up.
        
        Args:
            max_age_days: Maximum age of logs to keep
            
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        # Count expired logs by project
        expired_logs = db.session.query(
            DecisionLog.project_id,
            db.func.count(DecisionLog.id).label('count')
        ).filter(
            DecisionLog.created_at < cutoff_date
        ).group_by(DecisionLog.project_id).all()
        
        # Total expired logs
        total_expired = db.session.query(db.func.count(DecisionLog.id)).filter(
            DecisionLog.created_at < cutoff_date
        ).scalar()
        
        # Total logs
        total_logs = db.session.query(db.func.count(DecisionLog.id)).scalar()
        
        # Oldest log
        oldest_log = db.session.query(db.func.min(DecisionLog.created_at)).scalar()
        
        stats = {
            'total_logs': total_logs,
            'total_expired': total_expired,
            'cutoff_date': cutoff_date.isoformat(),
            'oldest_log_date': oldest_log.isoformat() if oldest_log else None,
            'expired_by_project': {project_id: count for project_id, count in expired_logs},
            'retention_days': max_age_days
        }
        
        logger.info(f"Cleanup stats: {total_expired}/{total_logs} logs expired (cutoff: {cutoff_date})")
        return stats
    
    def cleanup_expired_logs(self, max_age_days: int = 60, batch_size: int = 1000, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up expired decision logs.
        
        Args:
            max_age_days: Maximum age of logs to keep
            batch_size: Number of logs to process in each batch
            dry_run: If True, only count logs without deleting
            
        Returns:
            Dictionary with cleanup results
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        start_time = datetime.utcnow()
        
        logger.info(f"Starting decision log cleanup (max_age_days={max_age_days}, batch_size={batch_size}, dry_run={dry_run})")
        logger.info(f"Cutoff date: {cutoff_date}")
        
        total_deleted = 0
        batches_processed = 0
        
        try:
            while True:
                # Find expired logs in batches
                expired_logs = DecisionLog.query.filter(
                    DecisionLog.created_at < cutoff_date
                ).limit(batch_size).all()
                
                if not expired_logs:
                    break
                
                batch_count = len(expired_logs)
                batches_processed += 1
                
                if dry_run:
                    logger.info(f"Dry run - would delete batch {batches_processed}: {batch_count} logs")
                    total_deleted += batch_count
                    
                    # In dry run, we need to break to avoid infinite loop
                    # since we're not actually deleting anything
                    if batches_processed >= 10:  # Limit dry run to 10 batches for safety
                        logger.info("Dry run limited to 10 batches for safety")
                        break
                else:
                    # Delete the batch
                    for log in expired_logs:
                        db.session.delete(log)
                    
                    db.session.commit()
                    total_deleted += batch_count
                    
                    logger.info(f"Deleted batch {batches_processed}: {batch_count} logs (total: {total_deleted})")
                
                # Safety check to prevent runaway deletion
                if batches_processed >= 100:
                    logger.warning(f"Cleanup stopped after {batches_processed} batches for safety")
                    break
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'success': True,
                'total_deleted': total_deleted,
                'batches_processed': batches_processed,
                'duration_seconds': duration,
                'cutoff_date': cutoff_date.isoformat(),
                'dry_run': dry_run,
                'completed_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Cleanup completed: {total_deleted} logs {'would be ' if dry_run else ''}deleted in {duration:.2f}s")
            return result
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Cleanup failed after {batches_processed} batches: {str(e)}"
            logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'total_deleted': total_deleted,
                'batches_processed': batches_processed,
                'duration_seconds': (datetime.utcnow() - start_time).total_seconds(),
                'dry_run': dry_run
            }
    
    def _handle_cleanup_job(self, context: JobContext, **kwargs) -> JobResult:
        """Background job handler for decision log cleanup."""
        max_age_days = kwargs.get('max_age_days', 60)
        batch_size = kwargs.get('batch_size', 1000)
        dry_run = kwargs.get('dry_run', False)
        
        logger.info(f"Starting cleanup job {context.job_id}")
        
        try:
            # Update progress
            context.update_progress(10, "Starting cleanup...")
            
            # Get cleanup stats first
            stats = self.get_cleanup_stats(max_age_days)
            context.update_progress(20, f"Found {stats['total_expired']} expired logs")
            
            # Perform cleanup
            context.update_progress(30, "Cleaning up expired logs...")
            result = self.cleanup_expired_logs(max_age_days, batch_size, dry_run)
            
            if result['success']:
                context.update_progress(90, f"Cleanup completed: {result['total_deleted']} logs processed")
                
                # Combine stats and result
                final_result = {
                    'cleanup_result': result,
                    'initial_stats': stats,
                    'job_id': context.job_id
                }
                
                context.update_progress(100, "Cleanup job completed successfully")
                return JobResult.success(final_result)
            else:
                return JobResult.failure(result['error'], result)
                
        except Exception as e:
            error_msg = f"Cleanup job {context.job_id} failed: {str(e)}"
            logger.error(error_msg)
            return JobResult.failure(error_msg)
    
    def get_recent_cleanup_jobs(self, limit: int = 10) -> list:
        """Get recent cleanup job results."""
        jobs = BackgroundJob.query.filter_by(
            job_type=self.JOB_TYPE_CLEANUP
        ).order_by(
            BackgroundJob.created_at.desc()
        ).limit(limit).all()
        
        return [job.to_dict() for job in jobs]


# Global service instance
_cleanup_service = None


def get_cleanup_service() -> DecisionLogCleanupService:
    """Get the global cleanup service instance."""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = DecisionLogCleanupService()
    return _cleanup_service


def schedule_daily_cleanup(max_age_days: int = 60) -> int:
    """
    Convenience function to schedule daily cleanup.
    This would typically be called by a cron job or scheduler.
    """
    service = get_cleanup_service()
    return service.schedule_cleanup_job(max_age_days=max_age_days)


def cleanup_now(max_age_days: int = 60, dry_run: bool = False) -> Dict[str, Any]:
    """
    Convenience function to run cleanup immediately.
    Useful for manual cleanup or testing.
    """
    service = get_cleanup_service()
    return service.cleanup_expired_logs(max_age_days=max_age_days, dry_run=dry_run)
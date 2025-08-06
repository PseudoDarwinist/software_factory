"""
Background Job Management System
ThreadPoolExecutor-based job manager with database tracking and error recovery
"""

import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from flask import current_app
try:
    from ..models import BackgroundJob, db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import BackgroundJob, db


class JobResult:
    """Container for job execution results"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.utcnow()


class JobContext:
    """Context object passed to job functions for progress tracking and cancellation"""
    
    def __init__(self, job_id: int, job_manager: 'BackgroundJobManager'):
        self.job_id = job_id
        self.job_manager = job_manager
        self._cancelled = False
        self._lock = threading.Lock()
    
    def update_progress(self, progress: int, message: str = None):
        """Update job progress (0-100)"""
        with self._lock:
            if self._cancelled:
                raise JobCancelledException(f"Job {self.job_id} was cancelled")
            
            try:
                job = BackgroundJob.query.get(self.job_id)
                if job:
                    job.update_progress(progress)
                    if message:
                        current_app.logger.info(f"Job {self.job_id} progress: {progress}% - {message}")
            except Exception as e:
                current_app.logger.error(f"Failed to update job progress: {e}")
    
    def check_cancelled(self):
        """Check if job has been cancelled"""
        with self._lock:
            if self._cancelled:
                raise JobCancelledException(f"Job {self.job_id} was cancelled")
    
    def cancel(self):
        """Mark job as cancelled"""
        with self._lock:
            self._cancelled = True
    
    @property
    def is_cancelled(self):
        """Check if job is cancelled"""
        with self._lock:
            return self._cancelled


class JobCancelledException(Exception):
    """Exception raised when a job is cancelled"""
    pass


class BackgroundJobManager:
    """
    Background job manager using ThreadPoolExecutor with database tracking
    Provides job queue management, status tracking, and error recovery
    """
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_jobs: Dict[int, Future] = {}
        self.job_contexts: Dict[int, JobContext] = {}
        self._shutdown = False
        self._lock = threading.Lock()
        self.logger = None
        self.app = None
        
        # Job type handlers registry
        self.job_handlers: Dict[str, Callable] = {}
        
        # Cleanup thread for completed jobs
        self._cleanup_thread = None
        self._cleanup_interval = 300  # 5 minutes
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        self.logger = app.logger
        self.logger.info(f"Background job manager initialized with {self.executor._max_workers} workers")
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register default job handlers
        self._register_default_handlers()
    
    def register_job_handler(self, job_type: str, handler: Callable):
        """Register a handler function for a specific job type"""
        self.job_handlers[job_type] = handler
        self.logger.info(f"Registered handler for job type: {job_type}")
    
    def _register_default_handlers(self):
        """Register default job handlers"""
        # These will be implemented in subsequent tasks
        self.job_handlers[BackgroundJob.TYPE_REPOSITORY_PROCESSING] = self._handle_repository_processing
        self.job_handlers[BackgroundJob.TYPE_SYSTEM_MAP_GENERATION] = self._handle_system_map_generation
        self.job_handlers[BackgroundJob.TYPE_AI_ANALYSIS] = self._handle_ai_analysis
        self.job_handlers[BackgroundJob.TYPE_DATA_MIGRATION] = self._handle_data_migration
        # Spec generation will be registered by SpecGenerationService
    
    def submit_job(self, job_type: str, project_id: int = None, **kwargs) -> int:
        """
        Submit a new background job
        
        Args:
            job_type: Type of job to execute
            project_id: Optional project ID associated with the job
            **kwargs: Additional parameters for the job
        
        Returns:
            Job ID for tracking
        """
        if self._shutdown:
            raise RuntimeError("Job manager is shutting down")
        
        # Validate job type
        if job_type not in self.job_handlers:
            raise ValueError(f"No handler registered for job type: {job_type}")
        
        # Create job record in database (within app context)
        with self.app.app_context():
            job = BackgroundJob.create(job_type=job_type, project_id=project_id)
            db.session.commit()
            job_id = job.id
        
        # Create job context
        context = JobContext(job_id, self)
        
        with self._lock:
            self.job_contexts[job_id] = context
        
        # Submit job to executor
        future = self.executor.submit(self._execute_job, job_id, job_type, project_id, kwargs)
        
        with self._lock:
            self.active_jobs[job_id] = future
        
        self.logger.info(f"Submitted job {job_id} of type {job_type}")
        return job_id
    
    def _execute_job(self, job_id: int, job_type: str, project_id: int, kwargs: dict):
        """Execute a background job with error handling and progress tracking"""
        context = self.job_contexts.get(job_id)
        
        with self.app.app_context():
            try:
                # Get job record and mark as started
                job = BackgroundJob.query.get(job_id)
                if not job:
                    self.logger.error(f"Job {job_id} not found in database")
                    return
                
                job.start()
                self.logger.info(f"Starting job {job_id} of type {job_type}")
                
                # Check if handler exists
                if job_type not in self.job_handlers:
                    raise ValueError(f"No handler registered for job type: {job_type}")
                
                # Execute job handler
                handler = self.job_handlers[job_type]
                result = handler(context, project_id, **kwargs)
                
                # Mark job as completed
                if isinstance(result, JobResult):
                    if result.success:
                        job.complete(result.data)
                        self.logger.info(f"Job {job_id} completed successfully")
                    else:
                        job.fail(result.error)
                        self.logger.error(f"Job {job_id} failed: {result.error}")
                else:
                    job.complete(result)
                    self.logger.info(f"Job {job_id} completed successfully")
                
            except JobCancelledException:
                job = BackgroundJob.query.get(job_id)
                if job:
                    job.status = BackgroundJob.STATUS_CANCELLED
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                self.logger.info(f"Job {job_id} was cancelled")
                
            except Exception as e:
                # Handle job failure
                error_message = f"Job execution failed: {str(e)}"
                stack_trace = traceback.format_exc()
                
                job = BackgroundJob.query.get(job_id)
                if job:
                    job.fail(f"{error_message}\n\nStack trace:\n{stack_trace}")
                
                self.logger.error(f"Job {job_id} failed with exception: {e}")
                self.logger.debug(f"Job {job_id} stack trace: {stack_trace}")
                
            finally:
                # Cleanup job context and active job tracking
                with self._lock:
                    self.job_contexts.pop(job_id, None)
                    self.active_jobs.pop(job_id, None)
    
    def get_job_status(self, job_id: int) -> Optional[dict]:
        """Get status of a specific job"""
        with self.app.app_context():
            job = BackgroundJob.query.get(job_id)
            if job:
                return job.to_dict()
            return None
    
    def get_active_jobs(self) -> List[dict]:
        """Get list of all active jobs"""
        with self.app.app_context():
            active_jobs = BackgroundJob.query.filter(
                BackgroundJob.status.in_([BackgroundJob.STATUS_PENDING, BackgroundJob.STATUS_RUNNING])
            ).all()
            return [job.to_dict() for job in active_jobs]
    
    def get_project_jobs(self, project_id: int) -> List[dict]:
        """Get all jobs for a specific project"""
        with self.app.app_context():
            jobs = BackgroundJob.query.filter_by(project_id=project_id).order_by(
                BackgroundJob.created_at.desc()
            ).all()
            return [job.to_dict() for job in jobs]
    
    def cancel_job(self, job_id: int) -> bool:
        """Cancel a running job"""
        with self._lock:
            context = self.job_contexts.get(job_id)
            if context:
                context.cancel()
                self.logger.info(f"Cancelled job {job_id}")
                return True
            
            # If job is not in active contexts, check if it's pending in database
            with self.app.app_context():
                job = BackgroundJob.query.get(job_id)
                if job and job.status == BackgroundJob.STATUS_PENDING:
                    job.status = BackgroundJob.STATUS_CANCELLED
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                    self.logger.info(f"Cancelled pending job {job_id}")
                    return True
        
        return False
    
    def retry_job(self, job_id: int) -> Optional[int]:
        """Retry a failed job by creating a new job with same parameters"""
        with self.app.app_context():
            original_job = BackgroundJob.query.get(job_id)
            if not original_job or original_job.status != BackgroundJob.STATUS_FAILED:
                return None
            
            # Create new job with same parameters
            new_job_id = self.submit_job(
                job_type=original_job.job_type,
                project_id=original_job.project_id
            )
            
            self.logger.info(f"Retrying failed job {job_id} as new job {new_job_id}")
            return new_job_id
    
    def cleanup_completed_jobs(self, older_than_hours: int = 24):
        """Clean up completed jobs older than specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        with self.app.app_context():
            completed_jobs = BackgroundJob.query.filter(
                BackgroundJob.status.in_([
                    BackgroundJob.STATUS_COMPLETED,
                    BackgroundJob.STATUS_FAILED,
                    BackgroundJob.STATUS_CANCELLED
                ]),
                BackgroundJob.completed_at < cutoff_time
            ).all()
            
            count = len(completed_jobs)
            for job in completed_jobs:
                db.session.delete(job)
            
            db.session.commit()
            self.logger.info(f"Cleaned up {count} completed jobs older than {older_than_hours} hours")
            return count
    
    def get_system_stats(self) -> dict:
        """Get system statistics for monitoring"""
        with self.app.app_context():
            stats = {
                'active_jobs': len(self.active_jobs),
                'max_workers': self.executor._max_workers,
                'pending_jobs': BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_PENDING).count(),
                'running_jobs': BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_RUNNING).count(),
                'completed_jobs_24h': BackgroundJob.query.filter(
                    BackgroundJob.status == BackgroundJob.STATUS_COMPLETED,
                    BackgroundJob.completed_at > datetime.utcnow() - timedelta(hours=24)
                ).count(),
                'failed_jobs_24h': BackgroundJob.query.filter(
                    BackgroundJob.status == BackgroundJob.STATUS_FAILED,
                    BackgroundJob.completed_at > datetime.utcnow() - timedelta(hours=24)
                ).count(),
                'shutdown': self._shutdown
            }
            return stats
    
    def _start_cleanup_thread(self):
        """Start background thread for periodic cleanup"""
        def cleanup_worker():
            while not self._shutdown:
                try:
                    time.sleep(self._cleanup_interval)
                    if not self._shutdown:
                        self.cleanup_completed_jobs()
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Cleanup thread error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        self.logger.info("Started background cleanup thread")
    
    def shutdown(self):
        """Gracefully shutdown the job manager"""
        if self._shutdown:
            return
        
        self._shutdown = True
        self.logger.info("Shutting down background job manager...")
        
        # Cancel all active jobs
        with self._lock:
            for job_id, context in self.job_contexts.items():
                context.cancel()
        
        # Wait for jobs to complete
        self.executor.shutdown(wait=True)
        
        # Mark any remaining running jobs as failed
        with self.app.app_context():
            running_jobs = BackgroundJob.query.filter_by(status=BackgroundJob.STATUS_RUNNING).all()
            for job in running_jobs:
                job.fail("Job terminated due to system shutdown")
        
        self.logger.info("Background job manager shutdown complete")
    
    # Default job handlers (placeholder implementations)
    def _handle_repository_processing(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Handle repository processing job using the repository service"""
        try:
            from .repository import get_repository_service
            from ..models.mission_control_project import MissionControlProject
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from services.repository import get_repository_service
            from models.mission_control_project import MissionControlProject
        
        # Get repository URL from Mission Control project
        project = MissionControlProject.query.get(project_id)
        if not project or not project.repo_url:
            return JobResult(success=False, error="Mission Control Project not found or missing repository URL")
        
        # Use repository service to process the repository
        repository_service = get_repository_service()
        return repository_service.process_repository(context, project_id, project.repo_url)
    
    def _handle_system_map_generation(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Handle system map generation job (placeholder)"""
        context.update_progress(20, "Generating system map")
        time.sleep(1)  # Simulate work
        context.update_progress(100, "System map generated")
        
        return JobResult(success=True, data={"message": "System map generated successfully"})
    
    def _handle_ai_analysis(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Handle AI analysis job (placeholder)"""
        context.update_progress(30, "Running AI analysis")
        time.sleep(1)  # Simulate work
        context.update_progress(100, "AI analysis completed")
        
        return JobResult(success=True, data={"message": "AI analysis completed successfully"})
    
    def _handle_data_migration(self, context: JobContext, project_id: int, **kwargs) -> JobResult:
        """Handle data migration job (placeholder)"""
        context.update_progress(25, "Starting data migration")
        time.sleep(1)  # Simulate work
        context.update_progress(75, "Migrating data")
        time.sleep(1)  # Simulate work
        context.update_progress(100, "Data migration completed")
        
        return JobResult(success=True, data={"message": "Data migration completed successfully"})


# Global job manager instance
job_manager = None


def get_job_manager() -> BackgroundJobManager:
    """Get the global job manager instance"""
    global job_manager
    if job_manager is None:
        raise RuntimeError("Job manager not initialized. Call init_job_manager() first.")
    return job_manager


def init_job_manager(app, max_workers: int = 4) -> BackgroundJobManager:
    """Initialize the global job manager"""
    global job_manager
    job_manager = BackgroundJobManager(max_workers=max_workers)
    job_manager.init_app(app)
    return job_manager
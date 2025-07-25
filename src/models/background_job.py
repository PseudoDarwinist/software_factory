"""
Background Job model
"""

from datetime import datetime
from sqlalchemy import JSON
from .base import db


class BackgroundJob(db.Model):
    """Background job model for tracking asynchronous operations"""
    
    __tablename__ = 'background_job'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(100), nullable=True)  # Support both integer and string project IDs
    job_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)
    result = db.Column(JSON)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Valid job statuses
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    # Valid job types
    TYPE_REPOSITORY_PROCESSING = 'repository_processing'
    TYPE_SYSTEM_MAP_GENERATION = 'system_map_generation'
    TYPE_AI_ANALYSIS = 'ai_analysis'
    TYPE_DATA_MIGRATION = 'data_migration'
    
    def __repr__(self):
        return f'<BackgroundJob {self.id}: {self.job_type} ({self.status})>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'job_type': self.job_type,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'duration_seconds': self.get_duration_seconds()
        }
    
    @classmethod
    def create(cls, job_type, project_id=None):
        """Create a new background job"""
        if job_type not in [cls.TYPE_REPOSITORY_PROCESSING, cls.TYPE_SYSTEM_MAP_GENERATION, 
                           cls.TYPE_AI_ANALYSIS, cls.TYPE_DATA_MIGRATION]:
            raise ValueError(f"Invalid job type: {job_type}")
        
        job = cls(
            job_type=job_type,
            project_id=project_id,
            status=cls.STATUS_PENDING
        )
        
        db.session.add(job)
        return job
    
    def start(self):
        """Mark job as started"""
        self.status = self.STATUS_RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def complete(self, result=None):
        """Mark job as completed with optional result"""
        self.status = self.STATUS_COMPLETED
        self.progress = 100
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if result:
            self.result = result
        db.session.commit()
    
    def fail(self, error_message):
        """Mark job as failed with error message"""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_progress(self, progress):
        """Update job progress (0-100)"""
        if 0 <= progress <= 100:
            self.progress = progress
            self.updated_at = datetime.utcnow()
            db.session.commit()
    
    def get_duration_seconds(self):
        """Calculate job duration in seconds"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())
    
    def is_active(self):
        """Check if job is currently active (pending or running)"""
        return self.status in [self.STATUS_PENDING, self.STATUS_RUNNING]
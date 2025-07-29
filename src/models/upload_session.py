"""
Upload Session model for managing file upload sessions
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import text, String
from sqlalchemy.dialects.postgresql import UUID
from .base import db


class UploadSession(db.Model):
    """Upload session for managing batch file uploads and processing"""
    
    __tablename__ = 'upload_sessions'
    
    # Session status constants for 4-stage progress tracking
    STATUS_ACTIVE = 'active'
    STATUS_READING = 'reading'
    STATUS_ANALYZING = 'analyzing'
    STATUS_DRAFTING = 'drafting'
    STATUS_READY = 'ready'
    STATUS_COMPLETE = 'complete'
    STATUS_ERROR = 'error'
    
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id = db.Column(db.String(100), db.ForeignKey('mission_control_project.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)
    ai_model_used = db.Column(db.String(50))  # Track which AI model was used
    prd_preview = db.Column(db.Text)  # Quick PRD preview with source tags
    completeness_score = db.Column(db.JSON)  # PRD quality checklist scores
    combined_content = db.Column(db.Text)  # All extracted text combined
    ai_analysis = db.Column(db.Text)  # AI-generated insights
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = db.relationship('MissionControlProject', backref='upload_sessions')
    files = db.relationship('UploadedFile', backref='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UploadSession {self.id}: {self.status}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'description': self.description,
            'status': self.status,
            'ai_model_used': self.ai_model_used,
            'prd_preview': self.prd_preview,
            'completeness_score': self.completeness_score,
            'combined_content': self.combined_content,
            'ai_analysis': self.ai_analysis,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'files': [file.to_dict() for file in self.files] if self.files else []
        }
    
    @classmethod
    def create(cls, project_id, description=None):
        """Create a new upload session"""
        session = cls(
            project_id=project_id,
            description=description,
            status=cls.STATUS_ACTIVE
        )
        
        db.session.add(session)
        db.session.flush()  # Get the ID without committing
        return session
    
    def update_status(self, status):
        """Update session status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_combined_content(self, content):
        """Update combined content from all files"""
        self.combined_content = content
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_ai_analysis(self, analysis):
        """Update AI analysis results"""
        self.ai_analysis = analysis
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_processing_progress(self):
        """Calculate processing progress as a percentage"""
        if not self.files:
            return 0.0
        
        completed_files = sum(1 for file in self.files if file.processing_status == 'complete')
        return (completed_files / len(self.files)) * 100.0
    
    def is_processing_complete(self):
        """Check if all files have been processed"""
        if not self.files:
            return True
        
        return all(file.processing_status in ['complete', 'error'] for file in self.files)
    
    def has_processing_errors(self):
        """Check if any files have processing errors"""
        return any(file.processing_status == 'error' for file in self.files)
    
    def get_file_count(self):
        """Get total number of files in session"""
        return len(self.files) if self.files else 0
    
    def get_completed_file_count(self):
        """Get number of successfully processed files"""
        if not self.files:
            return 0
        return sum(1 for file in self.files if file.processing_status == 'complete')
    
    def get_error_file_count(self):
        """Get number of files with processing errors"""
        if not self.files:
            return 0
        return sum(1 for file in self.files if file.processing_status == 'error')
    
    def update_prd_preview(self, preview):
        """Update PRD preview with source tags"""
        self.prd_preview = preview
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_completeness_score(self, score):
        """Update completeness score for PRD quality checklist"""
        self.completeness_score = score
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_ai_model_used(self, model_name):
        """Update which AI model was used for processing"""
        self.ai_model_used = model_name
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_progress_stage(self):
        """Get current progress stage as percentage"""
        stage_progress = {
            self.STATUS_ACTIVE: 0.0,
            self.STATUS_READING: 0.25,
            self.STATUS_ANALYZING: 0.50,
            self.STATUS_DRAFTING: 0.75,
            self.STATUS_READY: 1.0,
            self.STATUS_COMPLETE: 1.0,
            self.STATUS_ERROR: 0.0
        }
        return stage_progress.get(self.status, 0.0)
"""
Uploaded File model for managing individual uploaded files
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import text, String
from sqlalchemy.dialects.postgresql import UUID
from .base import db


class UploadedFile(db.Model):
    """Individual uploaded file within an upload session"""
    
    __tablename__ = 'uploaded_files'
    
    # Processing status constants
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETE = 'complete'
    STATUS_ERROR = 'error'
    
    # Supported file types
    SUPPORTED_TYPES = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'url']
    
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = db.Column(String(36), db.ForeignKey('upload_sessions.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    page_count = db.Column(db.Integer)  # For PDF validation (Claude 100 page limit)
    source_id = db.Column(db.String(10))  # S1, S2, S3 for attribution
    extracted_text = db.Column(db.Text)  # Extracted content stored directly
    processing_status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UploadedFile {self.id}: {self.filename}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'session_id': str(self.session_id),
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_path': self.file_path,
            'page_count': self.page_count,
            'source_id': self.source_id,
            'extracted_text': self.extracted_text,
            'processing_status': self.processing_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def create(cls, session_id, filename, file_type, file_size, file_path, page_count=None):
        """Create a new uploaded file record"""
        # Auto-assign source ID based on existing files in session
        existing_files = cls.query.filter_by(session_id=session_id).count()
        source_id = f"S{existing_files + 1}"
        
        file_record = cls(
            session_id=session_id,
            filename=filename,
            file_type=file_type.lower(),
            file_size=file_size,
            file_path=file_path,
            page_count=page_count,
            source_id=source_id,
            processing_status=cls.STATUS_PENDING
        )
        
        db.session.add(file_record)
        db.session.flush()  # Get the ID without committing
        return file_record
    
    def update_processing_status(self, status):
        """Update file processing status"""
        self.processing_status = status
        db.session.commit()
    
    def update_extracted_text(self, text):
        """Update extracted text content"""
        self.extracted_text = text
        db.session.commit()
    
    def complete_processing(self, extracted_text=None):
        """Mark file processing as complete with optional extracted text"""
        self.processing_status = self.STATUS_COMPLETE
        if extracted_text:
            self.extracted_text = extracted_text
        db.session.commit()
    
    def mark_processing_error(self):
        """Mark file processing as failed"""
        self.processing_status = self.STATUS_ERROR
        db.session.commit()
    
    def is_supported_type(self):
        """Check if file type is supported for processing"""
        return self.file_type.lower() in self.SUPPORTED_TYPES
    
    def is_image_type(self):
        """Check if file is an image type"""
        return self.file_type.lower() in ['jpg', 'jpeg', 'png', 'gif']
    
    def is_pdf_type(self):
        """Check if file is a PDF"""
        return self.file_type.lower() == 'pdf'
    
    def is_url_type(self):
        """Check if file is a URL"""
        return self.file_type.lower() == 'url'
    
    def get_file_size_mb(self):
        """Get file size in megabytes"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @classmethod
    def get_by_session(cls, session_id):
        """Get all files for a specific session"""
        return cls.query.filter_by(session_id=session_id).all()
    
    @classmethod
    def get_pending_files(cls, session_id=None):
        """Get all pending files, optionally filtered by session"""
        query = cls.query.filter_by(processing_status=cls.STATUS_PENDING)
        if session_id:
            query = query.filter_by(session_id=session_id)
        return query.all()
    
    @classmethod
    def get_completed_files(cls, session_id=None):
        """Get all completed files, optionally filtered by session"""
        query = cls.query.filter_by(processing_status=cls.STATUS_COMPLETE)
        if session_id:
            query = query.filter_by(session_id=session_id)
        return query.all()
    
    def update_page_count(self, page_count):
        """Update page count for PDF files"""
        self.page_count = page_count
        db.session.commit()
    
    def get_source_tag(self):
        """Get formatted source tag for attribution"""
        return f"[{self.source_id}]" if self.source_id else "[S?]"
    
    def validate_for_ai_processing(self):
        """Validate file for AI processing based on type and size"""
        errors = []
        
        if self.is_pdf_type():
            # Claude Opus 4 limits: 32MB, 100 pages
            if self.file_size > 32 * 1024 * 1024:  # 32MB
                errors.append("PDF file exceeds 32MB limit for Claude processing")
            if self.page_count and self.page_count > 100:
                errors.append("PDF file exceeds 100 page limit for Claude processing")
        
        if self.file_size > 10 * 1024 * 1024:  # 10MB general limit
            errors.append("File exceeds 10MB upload limit")
        
        return errors
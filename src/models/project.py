"""
Project model
"""

from datetime import datetime
from .base import db


class Project(db.Model):
    """Project model representing a software project with repository information"""
    
    __tablename__ = 'project'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    repository_url = db.Column(db.String(500))
    status = db.Column(db.String(50), default='pending')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    system_maps = db.relationship('SystemMap', backref='project', lazy=True, cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='project', lazy=True, cascade='all, delete-orphan')
    background_jobs = db.relationship('BackgroundJob', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.id}: {self.name}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'repository_url': self.repository_url,
            'status': self.status,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'system_maps_count': len(self.system_maps) if self.system_maps else 0,
            'conversations_count': len(self.conversations) if self.conversations else 0
        }
    
    @classmethod
    def create(cls, name, repository_url=None, description=None):
        """Create a new project with validation"""
        if not name or not name.strip():
            raise ValueError("Project name is required")
        
        project = cls(
            name=name.strip(),
            repository_url=repository_url.strip() if repository_url else None,
            description=description.strip() if description else None
        )
        
        db.session.add(project)
        return project
    
    def update_status(self, new_status):
        """Update project status with timestamp"""
        self.status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
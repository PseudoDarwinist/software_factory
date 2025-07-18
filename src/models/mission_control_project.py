"""
Mission Control Project model - extends basic project with Mission Control specific fields
"""

from datetime import datetime
from sqlalchemy import JSON
from .base import db


class MissionControlProject(db.Model):
    """Mission Control specific project data"""
    
    __tablename__ = 'mission_control_project'
    
    # Health status levels
    HEALTH_GREEN = 'green'
    HEALTH_AMBER = 'amber'
    HEALTH_RED = 'red'
    
    # System map status
    SYSTEM_MAP_PENDING = 'pending'
    SYSTEM_MAP_IN_PROGRESS = 'in_progress'
    SYSTEM_MAP_COMPLETED = 'completed'
    SYSTEM_MAP_FAILED = 'failed'
    
    id = db.Column(db.String(100), primary_key=True)  # Support custom IDs like proj-1
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    repo_url = db.Column(db.String(500))
    health = db.Column(db.String(20), default=HEALTH_AMBER)
    unread_count = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    system_map_status = db.Column(db.String(50), default=SYSTEM_MAP_PENDING)
    meta_data = db.Column(JSON)  # Additional project metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<MissionControlProject {self.id}: {self.name}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'repoUrl': self.repo_url,
            'health': self.health,
            'unreadCount': self.unread_count,
            'lastActivity': self.last_activity.isoformat() if self.last_activity else None,
            'systemMapStatus': self.system_map_status,
            'metadata': self.meta_data or {},
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, id, name, description=None, repo_url=None, metadata=None):
        """Create a new Mission Control project"""
        project = cls(
            id=id,
            name=name,
            description=description,
            repo_url=repo_url,
            meta_data=metadata or {}
        )
        
        db.session.add(project)
        return project
    
    def update_health(self, health):
        """Update project health status"""
        self.health = health
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def increment_unread_count(self):
        """Increment unread count"""
        self.unread_count += 1
        self.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def decrement_unread_count(self):
        """Decrement unread count"""
        if self.unread_count > 0:
            self.unread_count -= 1
            self.updated_at = datetime.utcnow()
            db.session.commit()
    
    def update_system_map_status(self, status):
        """Update system map generation status"""
        self.system_map_status = status
        self.updated_at = datetime.utcnow()
        db.session.commit()
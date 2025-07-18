"""
System Map model
"""

from datetime import datetime
from sqlalchemy import JSON
from .base import db


class SystemMap(db.Model):
    """System map model storing generated repository analysis results"""
    
    __tablename__ = 'system_map'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    content = db.Column(JSON)
    version = db.Column(db.String(50), default='1.0')
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    generation_time_seconds = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<SystemMap {self.id} for Project {self.project_id}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'content': self.content,
            'version': self.version,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'generation_time_seconds': self.generation_time_seconds
        }
    
    @classmethod
    def create_for_project(cls, project_id, content, version='1.0', generation_time_seconds=None):
        """Create a new system map for a project"""
        if not content:
            raise ValueError("System map content is required")
        
        system_map = cls(
            project_id=project_id,
            content=content,
            version=version,
            generation_time_seconds=generation_time_seconds
        )
        
        db.session.add(system_map)
        return system_map
    
    def get_content_summary(self):
        """Get a summary of the system map content"""
        if not self.content:
            return "No content available"
        
        if isinstance(self.content, dict):
            components = self.content.get('components', [])
            dependencies = self.content.get('dependencies', [])
            return f"{len(components)} components, {len(dependencies)} dependencies"
        
        return "Content available"
"""
Channel Mapping model for Slack integration
"""

from datetime import datetime
from .base import db


class ChannelMapping(db.Model):
    """Channel to project mapping for external integrations like Slack"""
    
    __tablename__ = 'channel_mapping'
    
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(100), unique=True, nullable=False)
    project_id = db.Column(db.String(100), db.ForeignKey('mission_control_project.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to project (optional, for easier access)
    project = db.relationship('MissionControlProject', backref='channel_mappings')
    
    def __repr__(self):
        return f'<ChannelMapping {self.channel_id} -> {self.project_id}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'channelId': self.channel_id,
            'projectId': self.project_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, channel_id, project_id):
        """Create a new channel mapping"""
        mapping = cls(
            channel_id=channel_id,
            project_id=project_id
        )
        
        db.session.add(mapping)
        return mapping
    
    @classmethod
    def get_project_for_channel(cls, channel_id):
        """Get project ID for a channel"""
        mapping = cls.query.filter_by(channel_id=channel_id).first()
        return mapping.project_id if mapping else None
    
    @classmethod
    def set_mapping(cls, channel_id, project_id):
        """Set or update channel mapping"""
        mapping = cls.query.filter_by(channel_id=channel_id).first()
        if mapping:
            mapping.project_id = project_id
            mapping.updated_at = datetime.utcnow()
        else:
            mapping = cls.create(channel_id, project_id)
        
        db.session.commit()
        return mapping
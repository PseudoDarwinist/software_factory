"""
Feed Item model for Mission Control
"""

from datetime import datetime
from sqlalchemy import JSON
from .base import db


class FeedItem(db.Model):
    """Feed item model for Mission Control activity feed"""
    
    __tablename__ = 'feed_item'
    
    # Severity levels
    SEVERITY_INFO = 'info'
    SEVERITY_AMBER = 'amber'
    SEVERITY_RED = 'red'
    
    # Feed item kinds
    KIND_IDEA = 'idea'
    KIND_CI_FAIL = 'ci_fail'
    KIND_SPEC_CHANGE = 'spec_change'
    KIND_PR_REVIEW = 'pr_review'
    KIND_DEPLOYMENT = 'deployment'
    KIND_ALERT = 'alert'
    
    id = db.Column(db.String(100), primary_key=True)  # Support custom IDs like slack-xxx
    project_id = db.Column(db.String(100), nullable=False)  # Support custom project IDs
    severity = db.Column(db.String(20), nullable=False, default=SEVERITY_INFO)
    kind = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text)
    actor = db.Column(db.String(200))
    unread = db.Column(db.Boolean, default=True)
    linked_artifact_ids = db.Column(JSON)  # Array of artifact IDs
    meta_data = db.Column(JSON)  # Additional metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FeedItem {self.id}: {self.title[:50]}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'projectId': self.project_id,
            'severity': self.severity,
            'kind': self.kind,
            'title': self.title,
            'summary': self.summary,
            'actor': self.actor,
            'unread': self.unread,
            'linkedArtifactIds': self.linked_artifact_ids or [],
            'metadata': self.meta_data or {},
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create(cls, id, project_id, severity, kind, title, summary=None, actor=None, metadata=None):
        """Create a new feed item"""
        feed_item = cls(
            id=id,
            project_id=project_id,
            severity=severity,
            kind=kind,
            title=title,
            summary=summary,
            actor=actor,
            meta_data=metadata or {},
            linked_artifact_ids=[]
        )
        
        db.session.add(feed_item)
        return feed_item
    
    def mark_read(self):
        """Mark feed item as read"""
        self.unread = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def update_metadata(self, new_metadata):
        """Update metadata with new values"""
        if not self.meta_data:
            self.meta_data = {}
        self.meta_data.update(new_metadata)
        self.updated_at = datetime.utcnow()
        db.session.commit()
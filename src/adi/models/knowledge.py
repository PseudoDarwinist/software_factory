"""
Knowledge Model

Domain knowledge storage with semantic search capabilities.
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db


class Knowledge(db.Model):
    __tablename__ = 'adi_knowledge'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    rule_yaml = db.Column(db.Text)
    scope_filters = db.Column(JSONB, default=dict)
    source_link = db.Column(db.Text)
    author = db.Column(db.String(255), nullable=False)
    tags = db.Column(db.ARRAY(db.String), default=list)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Vector embedding for semantic search
    embedding = db.Column(db.ARRAY(db.Float))
    embedding_model = db.Column(db.String(100))
    embedding_generated_at = db.Column(db.DateTime)
    
    # Composite indexes for common queries
    __table_args__ = (
        db.Index('idx_project_author', 'project_id', 'author'),
        db.Index('idx_project_version', 'project_id', 'version'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<Knowledge {self.title[:50]} v{self.version}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'title': self.title,
            'content': self.content,
            'rule_yaml': self.rule_yaml,
            'scope_filters': self.scope_filters,
            'source_link': self.source_link,
            'author': self.author,
            'tags': self.tags,
            'version': self.version,
            'has_embedding': self.embedding is not None,
            'embedding_model': self.embedding_model,
            'embedding_generated_at': self.embedding_generated_at.isoformat() if self.embedding_generated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
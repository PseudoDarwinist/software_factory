"""
Insight Model

Permanent storage for generated insights from decision log analysis.
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


class Insight(db.Model):
    __tablename__ = 'adi_insights'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    kind = db.Column(db.String(100), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(10), nullable=False, index=True)  # low, med, high
    evidence = db.Column(JSONB, nullable=False)
    metrics = db.Column(JSONB, nullable=False)
    status = db.Column(db.String(20), default='open', index=True)  # open, converted, dismissed, resolved
    tags = db.Column(db.ARRAY(db.String), default=list)
    signature = db.Column(db.String(255), nullable=False, index=True)  # For clustering
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite indexes for common queries
    __table_args__ = (
        db.Index('idx_project_status', 'project_id', 'status'),
        db.Index('idx_project_severity', 'project_id', 'severity'),
        db.Index('idx_signature_project', 'signature', 'project_id'),
        db.Index('idx_kind_project', 'kind', 'project_id'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<Insight {self.kind} - {self.title[:50]}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'kind': self.kind,
            'title': self.title,
            'summary': self.summary,
            'severity': self.severity,
            'evidence': self.evidence,
            'metrics': self.metrics,
            'status': self.status,
            'tags': self.tags,
            'signature': self.signature,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
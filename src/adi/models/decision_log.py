"""
Decision Log Model

Temporary storage for decision logs from production applications.
"""

from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db


class DecisionLog(db.Model):
    __tablename__ = 'adi_decision_logs'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    case_id = db.Column(db.String(255), nullable=False, index=True)
    event_data = db.Column(JSONB, nullable=False)
    decision_data = db.Column(JSONB, nullable=False)
    version_data = db.Column(JSONB, nullable=False)
    links = db.Column(JSONB)
    hashes = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=60), index=True)
    
    # Composite indexes for common queries
    __table_args__ = (
        db.Index('idx_project_created', 'project_id', 'created_at'),
        db.Index('idx_case_project', 'case_id', 'project_id'),
        db.Index('idx_expires_cleanup', 'expires_at'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<DecisionLog {self.case_id} for {self.project_id}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'case_id': self.case_id,
            'event_data': self.event_data,
            'decision_data': self.decision_data,
            'version_data': self.version_data,
            'links': self.links,
            'hashes': self.hashes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
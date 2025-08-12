"""
Trend Model

Performance trends and metrics over time.
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db


class Trend(db.Model):
    __tablename__ = 'adi_trends'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    metric_key = db.Column(db.String(100), nullable=False, index=True)
    metric_value = db.Column(db.Numeric(10, 4), nullable=False)
    pack_version = db.Column(db.String(100), nullable=False)
    window_start = db.Column(db.DateTime, nullable=False, index=True)
    window_end = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_project_metric', 'project_id', 'metric_key'),
        db.Index('idx_project_window', 'project_id', 'window_start', 'window_end'),
        db.Index('idx_metric_window', 'metric_key', 'window_start'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<Trend {self.metric_key}={self.metric_value} for {self.project_id}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'metric_key': self.metric_key,
            'metric_value': float(self.metric_value),
            'pack_version': self.pack_version,
            'window_start': self.window_start.isoformat() if self.window_start else None,
            'window_end': self.window_end.isoformat() if self.window_end else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
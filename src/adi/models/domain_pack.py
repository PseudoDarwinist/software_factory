"""
Domain Pack Model

Snapshots of domain pack configurations for versioning and rollback.
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


class DomainPackSnapshot(db.Model):
    __tablename__ = 'adi_pack_snapshots'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    version = db.Column(db.String(100), nullable=False)
    pack_data = db.Column(JSONB, nullable=False)
    deployed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    factory_pr = db.Column(db.String(100))  # Software Factory PR number
    
    __table_args__ = (
        db.Index('idx_project_version', 'project_id', 'version'),
        db.Index('idx_project_deployed', 'project_id', 'deployed_at'),
        db.UniqueConstraint('project_id', 'version', name='uq_project_version'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<DomainPackSnapshot {self.project_id} v{self.version}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'version': self.version,
            'pack_data': self.pack_data,
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None,
            'factory_pr': self.factory_pr
        }
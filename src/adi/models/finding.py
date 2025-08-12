"""
Finding Model

Represents individual validation findings from decision log analysis.
Findings are temporary and get clustered into Insights.
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import Dict, Any, Optional, Literal
import uuid

try:
    from ...models.base import db
except ImportError:
    try:
        from src.models.base import db
    except ImportError:
        from models.base import db


class Finding(db.Model):
    __tablename__ = 'adi_findings'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    case_id = db.Column(db.String(255), nullable=False, index=True)
    kind = db.Column(db.String(100), nullable=False, index=True)  # e.g., "Time.SLA", "Template.Select"
    severity = db.Column(db.String(10), nullable=False, index=True)  # low, med, high
    details = db.Column(JSONB, nullable=False)
    suggested_fix = db.Column(db.Text)
    validator_name = db.Column(db.String(100), nullable=False)  # Which validator generated this
    signature = db.Column(db.String(255), nullable=False, index=True)  # For clustering
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # TTL for findings - they get clustered into insights and then cleaned up
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    
    # Composite indexes for common queries
    __table_args__ = (
        db.Index('idx_project_kind', 'project_id', 'kind'),
        db.Index('idx_signature_project', 'signature', 'project_id'),
        db.Index('idx_expires_at', 'expires_at'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<Finding {self.kind} - {self.case_id}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'case_id': self.case_id,
            'kind': self.kind,
            'severity': self.severity,
            'details': self.details,
            'suggested_fix': self.suggested_fix,
            'validator_name': self.validator_name,
            'signature': self.signature,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


# Data class for in-memory Finding representation (used by scoring pipeline)
from dataclasses import dataclass

@dataclass
class FindingData:
    """
    In-memory representation of a Finding for use in the scoring pipeline.
    Gets converted to Finding model for database storage.
    """
    kind: str                                    # e.g., "Time.SLA"
    severity: Literal["low", "med", "high"]     # Severity level
    details: Dict[str, Any]                     # Validation details
    suggested_fix: Optional[str] = None         # Suggested remediation
    validator_name: str = "unknown"             # Which validator generated this
    
    def to_model(self, project_id: str, case_id: str, signature: str, expires_at: datetime) -> Finding:
        """Convert to database model."""
        return Finding(
            project_id=project_id,
            case_id=case_id,
            kind=self.kind,
            severity=self.severity,
            details=self.details,
            suggested_fix=self.suggested_fix,
            validator_name=self.validator_name,
            signature=signature,
            expires_at=expires_at
        )
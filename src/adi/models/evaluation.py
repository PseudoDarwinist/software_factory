"""
Evaluation Models

Evaluation sets and results for domain pack testing.
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


class EvalSet(db.Model):
    __tablename__ = 'adi_eval_sets'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    blueprint = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to evaluation results (use callable to avoid string resolution conflicts)
    results = db.relationship(lambda: EvalResult, backref='eval_set', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_project_name', 'project_id', 'name'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<EvalSet {self.name} for {self.project_id}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'name': self.name,
            'blueprint': self.blueprint,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EvalResult(db.Model):
    __tablename__ = 'adi_eval_results'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eval_set_id = db.Column(UUID(as_uuid=True), db.ForeignKey('adi_eval_sets.id'), nullable=False, index=True)
    run_id = db.Column(db.String(255), nullable=False, index=True)
    pass_rate = db.Column(db.Numeric(5, 4), nullable=False)
    total_cases = db.Column(db.Integer, nullable=False)
    passed_cases = db.Column(db.Integer, nullable=False)
    failed_cases = db.Column(JSONB, nullable=False)  # List of case IDs
    pack_version = db.Column(db.String(100), nullable=False)
    run_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_eval_run', 'eval_set_id', 'run_timestamp'),
        db.Index('idx_pack_version', 'pack_version'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f'<EvalResult {self.run_id} - {self.pass_rate:.2%}>'
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'eval_set_id': str(self.eval_set_id),
            'run_id': self.run_id,
            'pass_rate': float(self.pass_rate),
            'total_cases': self.total_cases,
            'passed_cases': self.passed_cases,
            'failed_cases': self.failed_cases,
            'pack_version': self.pack_version,
            'run_timestamp': self.run_timestamp.isoformat() if self.run_timestamp else None
        }
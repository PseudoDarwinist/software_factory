"""
Validation Run model for tracking validation processes after PR merges
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import JSON
from .base import db


class ValidationStatus(Enum):
    """Status of validation runs"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class ValidationRun(db.Model):
    """
    Model for tracking validation runs triggered by PR merges
    """
    
    __tablename__ = 'validation_run'
    
    id = db.Column(db.String(100), primary_key=True)
    project_id = db.Column(db.String(100), nullable=False, index=True)
    task_id = db.Column(db.String(100), nullable=True, index=True)  # Optional link to task
    
    # PR and commit information
    pr_number = db.Column(db.Integer, nullable=False)
    commit_sha = db.Column(db.String(40), nullable=False)
    branch = db.Column(db.String(255), nullable=False)
    
    # Validation status and timing
    status = db.Column(db.Enum(ValidationStatus), default=ValidationStatus.INITIALIZING, nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    started_by = db.Column(db.String(100))  # User who triggered the validation
    
    # GitHub workflow tracking
    workflow_runs = db.Column(JSON, default=list)  # List of GitHub workflow run references
    
    # Validation metadata
    validation_metadata = db.Column(JSON, default=dict)  # Additional validation context
    
    # Tracking fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_project_status', 'project_id', 'status'),
        db.Index('idx_pr_commit', 'pr_number', 'commit_sha'),
    )
    
    def __repr__(self):
        return f'<ValidationRun {self.id}: PR#{self.pr_number} - {self.status.value}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        payload = {
            'id': self.id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'pr_number': self.pr_number,
            'commit_sha': self.commit_sha,
            'branch': self.branch,
            'status': self.status.value if self.status else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'started_by': self.started_by,
            'workflow_runs': self.workflow_runs or [],
            'metadata': self.validation_metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        # Surface lightweight checks on the run payload when provided via metadata
        try:
            meta_checks = (self.validation_metadata or {}).get('checks') or []
            if isinstance(meta_checks, list) and meta_checks:
                payload['checks'] = meta_checks
        except Exception:
            pass
        return payload
    
    # --- decision helpers ---------------------------------------------------
    def get_decisions(self):
        meta = self.validation_metadata or {}
        decisions = meta.get('decisions') or []
        # Ensure list type
        if not isinstance(decisions, list):
            decisions = []
        return decisions
    
    def add_decision(self, action: str, reason: str = None, user: str = None):
        import datetime as _dt
        meta = self.validation_metadata or {}
        decisions = meta.get('decisions') or []
        if not isinstance(decisions, list):
            decisions = []
        decisions.append({
            'action': action,
            'reason': reason,
            'user': user,
            'timestamp': _dt.datetime.utcnow().isoformat()
        })
        meta['decisions'] = decisions
        self.validation_metadata = meta
        # Do not commit here; caller should commit
    
    @classmethod
    def create_from_pr_merge(cls, project_id: str, pr_number: int, commit_sha: str, 
                           branch: str, started_by: str = None, task_id: str = None):
        """Create a new validation run from a PR merge event"""
        import uuid
        from datetime import datetime as _dt
        
        validation_run_id = f"val_{project_id}_{pr_number}_{str(uuid.uuid4())[:8]}"
        
        validation_run = cls(
            id=validation_run_id,
            project_id=project_id,
            task_id=task_id,
            pr_number=pr_number,
            commit_sha=commit_sha,
            branch=branch,
            started_by=started_by,
            status=ValidationStatus.INITIALIZING
        )

        # Initialize with empty checks - real validation data will be populated by actual systems
        validation_run.validation_metadata = {
            'checks': []
        }
        
        db.session.add(validation_run)
        return validation_run
    
    @classmethod
    def get_project_validation_runs(cls, project_id: str, limit: int = 10):
        """Get validation runs for a project, ordered by most recent"""
        return cls.query.filter_by(project_id=project_id)\
                      .order_by(cls.started_at.desc())\
                      .limit(limit).all()
    
    @classmethod
    def get_active_validation_runs(cls, project_id: str):
        """Get currently active validation runs for a project"""
        return cls.query.filter_by(project_id=project_id)\
                      .filter(cls.status.in_([ValidationStatus.INITIALIZING, ValidationStatus.RUNNING]))\
                      .order_by(cls.started_at.desc()).all()
    
    def update_status(self, status: ValidationStatus):
        """Update validation run status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status in [ValidationStatus.SUCCESS, ValidationStatus.FAILURE, ValidationStatus.CANCELLED]:
            self.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Broadcast status update
        self._broadcast_status_update()
    
    def add_workflow_run(self, workflow_run_data: dict):
        """Add a GitHub workflow run reference"""
        if not self.workflow_runs:
            self.workflow_runs = []
        
        self.workflow_runs.append(workflow_run_data)
        
        # Mark the JSON field as modified so SQLAlchemy detects the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'workflow_runs')
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def add_validation_check(self, check_id: str, name: str, check_type: str, 
                           status: str = 'pending', metadata: dict = None):
        """Add a validation check to this run"""
        import datetime as _dt
        
        if not self.validation_metadata:
            self.validation_metadata = {}
        
        if 'checks' not in self.validation_metadata:
            self.validation_metadata['checks'] = []
        
        # Remove existing check with same ID if it exists
        self.validation_metadata['checks'] = [
            c for c in self.validation_metadata['checks'] 
            if c.get('id') != check_id
        ]
        
        # Add new check
        check = {
            'id': check_id,
            'name': name,
            'type': check_type,
            'status': status,
            'timestamp': _dt.datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        self.validation_metadata['checks'].append(check)
        
        # Mark the JSON field as modified so SQLAlchemy detects the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, 'validation_metadata')
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Broadcast update
        self._broadcast_status_update()
    
    def update_validation_check(self, check_id: str, status: str = None, 
                              metadata: dict = None):
        """Update an existing validation check"""
        import datetime as _dt
        
        if not self.validation_metadata or 'checks' not in self.validation_metadata:
            return False
        
        # Find and update the check
        for check in self.validation_metadata['checks']:
            if check.get('id') == check_id:
                if status:
                    check['status'] = status
                if metadata:
                    check['metadata'].update(metadata)
                check['timestamp'] = _dt.datetime.utcnow().isoformat()
                
                # Mark the JSON field as modified
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(self, 'validation_metadata')
                
                self.updated_at = datetime.utcnow()
                db.session.commit()
                
                # Broadcast update
                self._broadcast_status_update()
                return True
        
        return False
    
    def _broadcast_status_update(self):
        """Broadcast validation run status update via WebSocket to the Mission Control UI.
        Emits to topic 'validation.runs'.
        """
        try:
            # Import here to avoid circular imports
            try:
                from ..services.websocket_server import get_websocket_server
            except ImportError:
                from services.websocket_server import get_websocket_server

            ws_server = get_websocket_server()
            if ws_server:
                run_payload = self.to_dict()
                # Project-scoped broadcast so only authorized clients receive it
                ws_server.broadcast_validation_run(self.project_id, run_payload)

        except Exception as e:
            # Don't fail the validation run if broadcasting fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to broadcast validation update for run {self.id}: {e}")
    
    def get_duration_seconds(self):
        """Get validation run duration in seconds"""
        if not self.completed_at:
            return None
        
        return (self.completed_at - self.started_at).total_seconds()
    
    def is_active(self):
        """Check if validation run is currently active"""
        return self.status in [ValidationStatus.INITIALIZING, ValidationStatus.RUNNING]
    
    def get_workflow_summary(self):
        """Get summary of workflow runs"""
        if not self.workflow_runs:
            return {
                'total': 0,
                'running': 0,
                'success': 0,
                'failure': 0
            }
        
        summary = {'total': len(self.workflow_runs), 'running': 0, 'success': 0, 'failure': 0}
        
        for workflow in self.workflow_runs:
            status = workflow.get('status', 'unknown')
            conclusion = workflow.get('conclusion', 'unknown')
            
            if status == 'completed':
                if conclusion == 'success':
                    summary['success'] += 1
                else:
                    summary['failure'] += 1
            else:
                summary['running'] += 1
        
        return summary
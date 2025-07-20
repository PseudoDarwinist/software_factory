"""
Event log model for standardized event envelope format with Postgres persistence.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .base import db


class EventLog(db.Model):
    """Event log table for audit trail and event replay capabilities."""
    
    __tablename__ = 'event_log'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Standardized event envelope fields
    event_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    correlation_id = db.Column(db.String(36), nullable=False, index=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    
    # Event payload as JSON
    payload = db.Column(db.Text, nullable=False)
    
    # Additional metadata
    source_agent = db.Column(db.String(100), index=True)
    project_id = db.Column(db.String(36), index=True)
    actor = db.Column(db.String(100), index=True)
    trace_id = db.Column(db.String(36), index=True)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, **kwargs):
        # Generate event_id if not provided
        if 'event_id' not in kwargs:
            kwargs['event_id'] = str(uuid.uuid4())
        
        # Generate correlation_id if not provided
        if 'correlation_id' not in kwargs:
            kwargs['correlation_id'] = str(uuid.uuid4())
        
        # Ensure payload is JSON string
        if 'payload' in kwargs and isinstance(kwargs['payload'], dict):
            kwargs['payload'] = json.dumps(kwargs['payload'])
        
        super().__init__(**kwargs)
    
    @property
    def payload_dict(self) -> Dict[str, Any]:
        """Get payload as dictionary."""
        try:
            return json.loads(self.payload) if self.payload else {}
        except json.JSONDecodeError:
            return {}
    
    @payload_dict.setter
    def payload_dict(self, value: Dict[str, Any]) -> None:
        """Set payload from dictionary."""
        self.payload = json.dumps(value) if value else "{}"
    
    @classmethod
    def create_from_event(cls, event, source_agent: Optional[str] = None, project_id: Optional[str] = None):
        """Create EventLog from BaseEvent instance."""
        from ..events.base import BaseEvent
        
        if not isinstance(event, BaseEvent):
            raise ValueError("event must be a BaseEvent instance")
        
        # Extract project_id from payload if not provided
        if not project_id:
            payload = event.get_payload()
            project_id = payload.get('project_id') or payload.get('aggregate_id')
        
        return cls(
            event_id=event.metadata.event_id,
            timestamp=event.metadata.timestamp,
            correlation_id=event.metadata.correlation_id,
            event_type=event.get_event_type(),
            payload=json.dumps(event.get_payload()),
            source_agent=source_agent,
            project_id=project_id,
            actor=event.metadata.actor,
            trace_id=event.metadata.trace_id
        )
    
    @classmethod
    def create_envelope(
        cls,
        event_type: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        source_agent: Optional[str] = None,
        project_id: Optional[str] = None,
        actor: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Create standardized event envelope."""
        return cls(
            event_type=event_type,
            payload=json.dumps(payload),
            correlation_id=correlation_id,
            source_agent=source_agent,
            project_id=project_id,
            actor=actor,
            trace_id=trace_id
        )
    
    def to_envelope_dict(self) -> Dict[str, Any]:
        """Convert to standardized envelope format."""
        return {
            'id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'event_type': self.event_type,
            'payload': self.payload_dict,
            'source_agent': self.source_agent,
            'project_id': self.project_id,
            'actor': self.actor,
            'trace_id': self.trace_id
        }
    
    @classmethod
    def get_events_by_project(cls, project_id: str, limit: int = 100, offset: int = 0):
        """Get events for a specific project."""
        return cls.query.filter_by(project_id=project_id)\
                      .order_by(cls.timestamp.desc())\
                      .limit(limit)\
                      .offset(offset)\
                      .all()
    
    @classmethod
    def get_events_by_correlation(cls, correlation_id: str):
        """Get all events with the same correlation ID."""
        return cls.query.filter_by(correlation_id=correlation_id)\
                      .order_by(cls.timestamp.asc())\
                      .all()
    
    @classmethod
    def get_events_by_type(cls, event_type: str, limit: int = 100, offset: int = 0):
        """Get events by type."""
        return cls.query.filter_by(event_type=event_type)\
                      .order_by(cls.timestamp.desc())\
                      .limit(limit)\
                      .offset(offset)\
                      .all()
    
    @classmethod
    def get_events_by_agent(cls, source_agent: str, limit: int = 100, offset: int = 0):
        """Get events by source agent."""
        return cls.query.filter_by(source_agent=source_agent)\
                      .order_by(cls.timestamp.desc())\
                      .limit(limit)\
                      .offset(offset)\
                      .all()
    
    @classmethod
    def get_recent_events(cls, hours: int = 24, limit: int = 100):
        """Get recent events within specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return cls.query.filter(cls.timestamp >= cutoff_time)\
                      .order_by(cls.timestamp.desc())\
                      .limit(limit)\
                      .all()
    
    @classmethod
    def cleanup_old_events(cls, days_old: int = 90) -> int:
        """Clean up events older than specified days."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count events to be deleted
        count = cls.query.filter(cls.timestamp < cutoff_date).count()
        
        # Delete old events
        cls.query.filter(cls.timestamp < cutoff_date).delete()
        db.session.commit()
        
        return count
    
    def __repr__(self):
        return f'<EventLog {self.event_type} {self.event_id}>'
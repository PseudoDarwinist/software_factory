#!/usr/bin/env python3
"""
Event System - Event Schema and Management
Event-driven architecture foundation for Software Factory
"""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(Enum):
    """Standard event types for Software Factory workflows"""
    
    # Project lifecycle events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    
    # Idea and concept events
    IDEA_CREATED = "idea.created"
    IDEA_UPDATED = "idea.updated"
    IDEA_APPROVED = "idea.approved"
    IDEA_REJECTED = "idea.rejected"
    
    # Specification events
    SPEC_CREATED = "spec.created"
    SPEC_UPDATED = "spec.updated"
    SPEC_FROZEN = "spec.frozen"
    SPEC_APPROVED = "spec.approved"
    
    # Task management events
    TASKS_CREATED = "tasks.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # Development events
    CODE_GENERATED = "code.generated"
    CODE_REVIEWED = "code.reviewed"
    CODE_MERGED = "code.merged"
    
    # Build and deployment events
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"
    
    # AI and automation events
    AI_PROCESSING_STARTED = "ai.processing.started"
    AI_PROCESSING_COMPLETED = "ai.processing.completed"
    AI_PROCESSING_FAILED = "ai.processing.failed"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health.check"
    SYSTEM_ERROR = "system.error"
    USER_ACTION = "user.action"


@dataclass
class Event:
    """Standard event structure for all Software Factory events"""
    
    event_type: str
    event_id: str
    timestamp: float
    source: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate event structure"""
        if not self.event_id:
            raise ValueError("Event ID is required")
        if not self.event_type:
            raise ValueError("Event type is required")
        if not self.source:
            raise ValueError("Event source is required")
        if self.timestamp <= 0:
            raise ValueError("Timestamp must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Create event from JSON string"""
        return cls.from_dict(json.loads(json_str))


class EventBuilder:
    """Builder pattern for creating events with proper defaults"""
    
    def __init__(self, event_type: EventType):
        self.event_type = event_type.value
        self.timestamp = time.time()
        self.data = {}
        self.metadata = {}
        self.correlation_id = None
        self.user_id = None
        self.project_id = None
        self.source = "software_factory"
        self.event_id = None
    
    def with_id(self, event_id: str) -> 'EventBuilder':
        """Set event ID"""
        self.event_id = event_id
        return self
    
    def with_source(self, source: str) -> 'EventBuilder':
        """Set event source"""
        self.source = source
        return self
    
    def with_data(self, data: Dict[str, Any]) -> 'EventBuilder':
        """Set event data"""
        self.data = data
        return self
    
    def with_metadata(self, metadata: Dict[str, Any]) -> 'EventBuilder':
        """Set event metadata"""
        self.metadata = metadata
        return self
    
    def with_correlation_id(self, correlation_id: str) -> 'EventBuilder':
        """Set correlation ID for event tracing"""
        self.correlation_id = correlation_id
        return self
    
    def with_user_id(self, user_id: str) -> 'EventBuilder':
        """Set user ID"""
        self.user_id = user_id
        return self
    
    def with_project_id(self, project_id: str) -> 'EventBuilder':
        """Set project ID"""
        self.project_id = project_id
        return self
    
    def build(self) -> Event:
        """Build the event"""
        if not self.event_id:
            import uuid
            self.event_id = str(uuid.uuid4())
        
        return Event(
            event_type=self.event_type,
            event_id=self.event_id,
            timestamp=self.timestamp,
            source=self.source,
            data=self.data,
            metadata=self.metadata,
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            project_id=self.project_id
        )


class EventValidator:
    """Validate events against expected schemas"""
    
    @staticmethod
    def validate_event(event: Event) -> bool:
        """Validate basic event structure"""
        try:
            if not event.event_id or not event.event_type or not event.source:
                return False
            if event.timestamp <= 0:
                return False
            if not isinstance(event.data, dict):
                return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_event_data(event: Event, required_fields: List[str]) -> bool:
        """Validate that event data contains required fields"""
        try:
            for field in required_fields:
                if field not in event.data:
                    return False
            return True
        except Exception:
            return False


# Event schema definitions for common Software Factory events
EVENT_SCHEMAS = {
    EventType.PROJECT_CREATED.value: {
        "required_fields": ["project_name", "created_by"],
        "optional_fields": ["description", "template", "initial_requirements"]
    },
    
    EventType.IDEA_CREATED.value: {
        "required_fields": ["idea_title", "description", "created_by"],
        "optional_fields": ["tags", "priority", "business_value"]
    },
    
    EventType.SPEC_FROZEN.value: {
        "required_fields": ["spec_id", "version", "frozen_by"],
        "optional_fields": ["change_summary", "approval_required"]
    },
    
    EventType.TASKS_CREATED.value: {
        "required_fields": ["task_count", "created_from", "assigned_to"],
        "optional_fields": ["estimated_effort", "due_date", "dependencies"]
    },
    
    EventType.CODE_GENERATED.value: {
        "required_fields": ["files_generated", "generator", "task_id"],
        "optional_fields": ["test_coverage", "quality_score", "review_required"]
    },
    
    EventType.AI_PROCESSING_STARTED.value: {
        "required_fields": ["process_type", "input_data", "processor"],
        "optional_fields": ["estimated_duration", "priority", "retry_count"]
    }
}


def create_event(event_type: EventType, **kwargs) -> Event:
    """Convenience function to create events with proper defaults"""
    builder = EventBuilder(event_type)
    
    # Set common attributes from kwargs
    if 'source' in kwargs:
        builder.with_source(kwargs.pop('source'))
    if 'correlation_id' in kwargs:
        builder.with_correlation_id(kwargs.pop('correlation_id'))
    if 'user_id' in kwargs:
        builder.with_user_id(kwargs.pop('user_id'))
    if 'project_id' in kwargs:
        builder.with_project_id(kwargs.pop('project_id'))
    if 'metadata' in kwargs:
        builder.with_metadata(kwargs.pop('metadata'))
    
    # Remaining kwargs become event data
    if kwargs:
        builder.with_data(kwargs)
    
    return builder.build()


def validate_event_schema(event: Event) -> bool:
    """Validate event against its schema if defined"""
    schema = EVENT_SCHEMAS.get(event.event_type)
    if not schema:
        return EventValidator.validate_event(event)
    
    # Check basic structure
    if not EventValidator.validate_event(event):
        return False
    
    # Check required fields
    required_fields = schema.get("required_fields", [])
    if not EventValidator.validate_event_data(event, required_fields):
        return False
    
    return True
"""
Base event classes and metadata structures for the event-driven architecture.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum


class EventVersion(Enum):
    """Event schema versions for backward compatibility."""
    V1 = "1.0"
    V2 = "2.0"


@dataclass
class EventMetadata:
    """Metadata for all events including correlation tracking and versioning."""
    
    event_id: str
    correlation_id: str
    timestamp: datetime
    event_version: str
    source_service: str
    actor: Optional[str] = None
    trace_id: Optional[str] = None
    
    def __post_init__(self):
        """Ensure timestamp is in ISO format for serialization."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMetadata':
        """Create metadata from dictionary."""
        return cls(**data)


class BaseEvent(ABC):
    """Abstract base class for all domain events."""
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        actor: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        self.metadata = EventMetadata(
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id or str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_version=self.get_version(),
            source_service="software-factory",
            actor=actor,
            trace_id=trace_id
        )
    
    @abstractmethod
    def get_event_type(self) -> str:
        """Return the event type identifier."""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Return the event schema version."""
        pass
    
    @abstractmethod
    def get_payload(self) -> Dict[str, Any]:
        """Return the event payload data."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            'event_type': self.get_event_type(),
            'metadata': self.metadata.to_dict(),
            'payload': self.get_payload()
        }
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEvent':
        """Deserialize event from dictionary."""
        # This will be implemented by concrete event classes
        raise NotImplementedError("Subclasses must implement from_dict")
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseEvent':
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class DomainEvent(BaseEvent):
    """Base class for domain-specific events."""
    
    def __init__(
        self,
        aggregate_id: str,
        aggregate_type: str,
        correlation_id: Optional[str] = None,
        actor: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        super().__init__(correlation_id, actor, trace_id)
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
    
    def get_payload(self) -> Dict[str, Any]:
        """Base payload includes aggregate information."""
        return {
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type
        }


class SystemEvent(BaseEvent):
    """Base class for system-level events."""
    
    def __init__(
        self,
        component: str,
        correlation_id: Optional[str] = None,
        actor: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        super().__init__(correlation_id, actor, trace_id)
        self.component = component
    
    def get_payload(self) -> Dict[str, Any]:
        """Base payload includes component information."""
        return {
            'component': self.component
        }


class EventFilter:
    """Filter for event subscriptions and routing."""
    
    def __init__(
        self,
        event_types: Optional[List[str]] = None,
        aggregate_types: Optional[List[str]] = None,
        actors: Optional[List[str]] = None,
        correlation_ids: Optional[List[str]] = None
    ):
        self.event_types = event_types or []
        self.aggregate_types = aggregate_types or []
        self.actors = actors or []
        self.correlation_ids = correlation_ids or []
    
    def matches(self, event: BaseEvent) -> bool:
        """Check if event matches this filter."""
        # Check event type
        if self.event_types and event.get_event_type() not in self.event_types:
            return False
        
        # Check aggregate type for domain events
        if (self.aggregate_types and 
            isinstance(event, DomainEvent) and 
            event.aggregate_type not in self.aggregate_types):
            return False
        
        # Check actor
        if (self.actors and 
            event.metadata.actor and 
            event.metadata.actor not in self.actors):
            return False
        
        # Check correlation ID
        if (self.correlation_ids and 
            event.metadata.correlation_id not in self.correlation_ids):
            return False
        
        return True
"""
Base agent class for intelligent event-driven agents.
"""

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from concurrent.futures import ThreadPoolExecutor, Future

try:
    from ..events.base import BaseEvent, EventFilter
    from ..events.event_router import EventBus, SubscriptionType
    from ..services.metrics_service import get_metrics_service
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from events.base import BaseEvent, EventFilter
    from events.event_router import EventBus, SubscriptionType
    from services.metrics_service import get_metrics_service


logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    
    agent_id: str
    name: str
    description: str
    event_types: List[str] = field(default_factory=list)
    aggregate_types: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)
    max_concurrent_events: int = 5
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 300.0  # 5 minutes
    enable_dead_letter_queue: bool = True
    loop_detection_window_minutes: int = 10
    max_events_per_window: int = 100


@dataclass
class ProjectContext:
    """Represents the context for a specific project."""
    project_id: str
    project_name: Optional[str] = None
    repo_url: Optional[str] = None
    system_map: Optional[Dict[str, Any]] = None


@dataclass
class EventProcessingResult:
    """Result of processing an event."""
    
    success: bool
    agent_id: str
    event_id: str
    event_type: str
    processing_time_seconds: float
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    generated_events: List[BaseEvent] = field(default_factory=list)


class BaseAgent(ABC):
    """Base class for intelligent agents that react to events."""
    
    def __init__(self, config: AgentConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.status = AgentStatus.STOPPED
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_events)
        self.active_tasks: Dict[str, Future] = {}
        self.processed_events: Set[str] = set()
        self.event_history: List[Dict[str, Any]] = []
        self.loop_detection_cache: Dict[str, List[datetime]] = {}
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._subscription_id = f"{config.agent_id}_subscription"
        
        # Get metrics service for monitoring
        self.metrics_service = get_metrics_service()
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'events_succeeded': 0,
            'events_failed': 0,
            'total_processing_time': 0.0,
            'started_at': None,
            'last_event_at': None
        }
    
    def start(self) -> None:
        """Start the agent and begin processing events."""
        with self._lock:
            if self.status != AgentStatus.STOPPED:
                logger.warning(f"Agent {self.config.agent_id} is already running")
                return
            
            self.status = AgentStatus.STARTING
            logger.info(f"Starting agent {self.config.agent_id}")
            
            try:
                # Subscribe to events
                event_filter = EventFilter(
                    event_types=self.config.event_types,
                    aggregate_types=self.config.aggregate_types,
                    actors=self.config.actors
                )
                
                self.event_bus.event_router.subscribe(
                    subscription_id=self._subscription_id,
                    event_filter=event_filter,
                    handler=self._handle_event,
                    subscription_type=SubscriptionType.BACKGROUND,
                    max_retries=self.config.retry_attempts,
                    retry_delay_seconds=self.config.retry_delay_seconds,
                    dead_letter_queue=self.config.enable_dead_letter_queue
                )
                
                self.status = AgentStatus.RUNNING
                self.stats['started_at'] = datetime.utcnow()
                
                # Update metrics
                self.metrics_service.set_agent_status(self.config.agent_id, "running")
                
                logger.info(f"Agent {self.config.agent_id} started successfully")
                
            except Exception as e:
                self.status = AgentStatus.ERROR
                logger.error(f"Failed to start agent {self.config.agent_id}: {e}")
                raise
    
    def stop(self) -> None:
        """Stop the agent and clean up resources."""
        with self._lock:
            if self.status == AgentStatus.STOPPED:
                return
            
            self.status = AgentStatus.SHUTTING_DOWN
            logger.info(f"Stopping agent {self.config.agent_id}")
            
            # Signal shutdown
            self._shutdown_event.set()
            
            # Unsubscribe from events
            self.event_bus.event_router.unsubscribe(self._subscription_id)
            
            # Wait for active tasks to complete (with timeout)
            self._wait_for_active_tasks(timeout_seconds=30)
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
            self.status = AgentStatus.STOPPED
            
            # Update metrics
            self.metrics_service.set_agent_status(self.config.agent_id, "stopped")
            
            logger.info(f"Agent {self.config.agent_id} stopped")
    
    def pause(self) -> None:
        """Pause the agent (stop processing new events)."""
        with self._lock:
            if self.status == AgentStatus.RUNNING:
                self.event_bus.event_router.deactivate_subscription(self._subscription_id)
                self.status = AgentStatus.PAUSED
                self.metrics_service.set_agent_status(self.config.agent_id, "paused")
                logger.info(f"Agent {self.config.agent_id} paused")
    
    def resume(self) -> None:
        """Resume the agent (start processing events again)."""
        with self._lock:
            if self.status == AgentStatus.PAUSED:
                self.event_bus.event_router.activate_subscription(self._subscription_id)
                self.status = AgentStatus.RUNNING
                self.metrics_service.set_agent_status(self.config.agent_id, "running")
                logger.info(f"Agent {self.config.agent_id} resumed")
    
    def _handle_event(self, event: BaseEvent) -> None:
        """Handle incoming events (called by event router)."""
        if self._shutdown_event.is_set():
            return
        
        # Check for duplicate processing
        if event.metadata.event_id in self.processed_events:
            logger.debug(f"Event {event.metadata.event_id} already processed by agent {self.config.agent_id}")
            return
        
        # Check for infinite loops
        if self._detect_infinite_loop(event):
            logger.warning(f"Infinite loop detected for agent {self.config.agent_id}, skipping event {event.metadata.event_id}")
            return
        
        # Submit for background processing
        task_id = str(uuid.uuid4())
        future = self.executor.submit(self._process_event_with_timeout, event, task_id)
        
        with self._lock:
            self.active_tasks[task_id] = future
            # Update active tasks metric
            self.metrics_service.set_agent_active_tasks(self.config.agent_id, len(self.active_tasks))
        
        # Clean up completed tasks
        self._cleanup_completed_tasks()
    
    def _process_event_with_timeout(self, event: BaseEvent, task_id: str) -> EventProcessingResult:
        """Process event with timeout handling."""
        start_time = time.time()
        
        try:
            # Set timeout
            future = self.executor.submit(self._process_event_safely, event)
            result = future.result(timeout=self.config.timeout_seconds)
            
            processing_time = time.time() - start_time
            
            # Update statistics and metrics
            with self._lock:
                self.stats['events_processed'] += 1
                self.stats['total_processing_time'] += processing_time
                self.stats['last_event_at'] = datetime.utcnow()
                
                if result.success:
                    self.stats['events_succeeded'] += 1
                    self.increment_metric(event.get_event_type(), "success")
                else:
                    self.stats['events_failed'] += 1
                    self.increment_metric(event.get_event_type(), "failure")
                
                # Record processing time
                self.metrics_service.record_agent_processing_time(
                    agent_id=self.config.agent_id,
                    event_type=event.get_event_type(),
                    duration=processing_time
                )
                
                # Mark as processed
                self.processed_events.add(event.metadata.event_id)
                
                # Add to history
                self.event_history.append({
                    'event_id': event.metadata.event_id,
                    'event_type': event.get_event_type(),
                    'processed_at': datetime.utcnow(),
                    'success': result.success,
                    'processing_time': processing_time,
                    'error_message': result.error_message
                })
                
                # Limit history size
                if len(self.event_history) > 1000:
                    self.event_history = self.event_history[-500:]
            
            # Publish any generated events
            if result.generated_events:
                for generated_event in result.generated_events:
                    self.publish_event(generated_event)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Event processing failed for agent {self.config.agent_id}: {e}")
            
            with self._lock:
                self.stats['events_processed'] += 1
                self.stats['events_failed'] += 1
                self.stats['total_processing_time'] += processing_time
                self.stats['last_event_at'] = datetime.utcnow()
                
                # Track failure metrics
                self.increment_metric(event.get_event_type(), "failure")
                self.metrics_service.record_agent_processing_time(
                    agent_id=self.config.agent_id,
                    event_type=event.get_event_type(),
                    duration=processing_time
                )
            
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
        
        finally:
            # Remove from active tasks
            with self._lock:
                self.active_tasks.pop(task_id, None)
                # Update active tasks metric
                self.metrics_service.set_agent_active_tasks(self.config.agent_id, len(self.active_tasks))
    
    def _process_event_safely(self, event: BaseEvent) -> EventProcessingResult:
        """Safely process an event with error handling."""
        try:
            result = self.process_event(event)
            return result
        except Exception as e:
            logger.error(f"Agent {self.config.agent_id} failed to process event {event.metadata.event_id}: {e}")
            return EventProcessingResult(
                success=False,
                agent_id=self.config.agent_id,
                event_id=event.metadata.event_id,
                event_type=event.get_event_type(),
                processing_time_seconds=0.0,
                error_message=str(e)
            )
    
    def _detect_infinite_loop(self, event: BaseEvent) -> bool:
        """Detect potential infinite loops based on event patterns."""
        event_key = f"{event.get_event_type()}:{event.metadata.correlation_id}"
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(minutes=self.config.loop_detection_window_minutes)
        
        # Get or create event timestamps for this key
        if event_key not in self.loop_detection_cache:
            self.loop_detection_cache[event_key] = []
        
        timestamps = self.loop_detection_cache[event_key]
        
        # Remove old timestamps outside the window
        timestamps[:] = [ts for ts in timestamps if ts > window_start]
        
        # Add current timestamp
        timestamps.append(current_time)
        
        # Check if we've exceeded the threshold
        if len(timestamps) > self.config.max_events_per_window:
            logger.warning(f"Potential infinite loop detected: {len(timestamps)} events of type {event_key} in {self.config.loop_detection_window_minutes} minutes")
            return True
        
        return False
    
    def _cleanup_completed_tasks(self) -> None:
        """Clean up completed tasks from active tasks dict."""
        with self._lock:
            completed_tasks = [
                task_id for task_id, future in self.active_tasks.items()
                if future.done()
            ]
            
            for task_id in completed_tasks:
                self.active_tasks.pop(task_id, None)
    
    def _wait_for_active_tasks(self, timeout_seconds: int = 30) -> None:
        """Wait for active tasks to complete."""
        start_time = time.time()
        
        while self.active_tasks and (time.time() - start_time) < timeout_seconds:
            time.sleep(0.1)
            self._cleanup_completed_tasks()
        
        if self.active_tasks:
            logger.warning(f"Agent {self.config.agent_id} has {len(self.active_tasks)} tasks still running after timeout")
    
    def get_project_context(self, project_id: str) -> ProjectContext:
        """Retrieve project context for AI processing."""
        try:
            # Import here to avoid circular imports
            try:
                from ..models.mission_control_project import MissionControlProject
                from ..models import SystemMap
                from ..models.base import db
            except ImportError:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from models.mission_control_project import MissionControlProject
                from models import SystemMap
                from models.base import db
            
            # Use MissionControlProject which has string IDs
            project = MissionControlProject.query.filter_by(id=project_id).first()
            
            if not project:
                logger.warning(f"Project {project_id} not found")
                return ProjectContext(project_id=project_id)
            
            # Get system map by finding the regular project ID stored in metadata
            system_map_data = None
            regular_project_id = None
            
            if project.meta_data and project.meta_data.get('regular_project_id'):
                regular_project_id = project.meta_data.get('regular_project_id')
                logger.info(f"Found regular project ID {regular_project_id} for Mission Control project {project_id}")
                
                # Get the latest system map for this regular project
                system_map = SystemMap.query.filter_by(project_id=regular_project_id)\
                                          .order_by(SystemMap.generated_at.desc())\
                                          .first()
                
                if system_map:
                    system_map_data = system_map.content
                    logger.info(f"Retrieved system map for project {regular_project_id}")
                else:
                    logger.warning(f"No system map found for regular project {regular_project_id}")
            else:
                logger.warning(f"No regular project ID mapping found for Mission Control project {project_id}")
            
            actual_project_id = project.id
            
            return ProjectContext(
                project_id=str(actual_project_id),
                system_map=system_map_data,
                git_repository=project.repo_url,
                external_integrations={}
            )
            
        except Exception as e:
            logger.error(f"Failed to get project context for {project_id}: {e}")
            return ProjectContext(project_id=project_id)
    
    def get_vector_context(self, query: str, project_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similar documents using vector search."""
        try:
            # Import here to avoid circular imports
            from ..services.vector_service import VectorService
            
            vector_service = VectorService()
            results = vector_service.search_similar_documents(
                query=query,
                project_id=project_id,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get vector context: {e}")
            return []
    
    def get_graph_relationships(self, entity_id: str, entity_type: str = "project") -> Dict[str, Any]:
        """Retrieve graph relationships for an entity."""
        try:
            # Import here to avoid circular imports
            from ..services.graph_service import GraphService
            
            graph_service = GraphService()
            relationships = graph_service.get_entity_relationships(
                entity_id=entity_id,
                entity_type=entity_type
            )
            
            return relationships
            
        except Exception as e:
            logger.error(f"Failed to get graph relationships: {e}")
            return {}
    
    def publish_event(self, event: BaseEvent, project_id: Optional[str] = None) -> None:
        """Publish an event to the event bus with metrics tracking."""
        try:
            # Publish event with agent source and project context
            result = self.event_bus.publish(
                event=event,
                source_agent=self.config.agent_id,
                project_id=project_id
            )
            
            # Track metrics
            self.metrics_service.increment_event_published(
                event_type=event.get_event_type(),
                source=self.config.agent_id
            )
            
            logger.debug(f"Agent {self.config.agent_id} published event {event.get_event_type()}")
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            self.metrics_service.increment_event_published(
                event_type=event.get_event_type(),
                source=f"{self.config.agent_id}_failed"
            )
    
    def increment_metric(self, event_type: str, status: str) -> None:
        """Increment agent metrics."""
        self.metrics_service.increment_agent_event(
            agent_id=self.config.agent_id,
            event_type=event_type,
            status=status
        )
    
    @abstractmethod
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process a single event. Must be implemented by subclasses."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and statistics."""
        with self._lock:
            return {
                'agent_id': self.config.agent_id,
                'name': self.config.name,
                'status': self.status.value,
                'active_tasks': len(self.active_tasks),
                'processed_events_count': len(self.processed_events),
                'stats': self.stats.copy(),
                'config': {
                    'event_types': self.config.event_types,
                    'aggregate_types': self.config.aggregate_types,
                    'max_concurrent_events': self.config.max_concurrent_events,
                    'timeout_seconds': self.config.timeout_seconds
                }
            }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent processed events."""
        with self._lock:
            return self.event_history[-limit:] if self.event_history else []
    
    def clear_processed_events(self) -> int:
        """Clear processed events cache and return count."""
        with self._lock:
            count = len(self.processed_events)
            self.processed_events.clear()
            self.event_history.clear()
            self.loop_detection_cache.clear()
            return count
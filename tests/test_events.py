"""
Tests for the event-driven domain model and event system.
"""

import unittest
import tempfile
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.events.base import BaseEvent, DomainEvent, EventFilter, EventMetadata
from src.events.domain_events import (
    ProjectCreatedEvent, ProjectUpdatedEvent, RepositoryProcessingStartedEvent,
    AIRequestStartedEvent, BuildStartedEvent, IdeaCreatedEvent, SpecFrozenEvent
)
from src.events.event_store import EventStore
from src.events.event_router import EventRouter, EventBus, SubscriptionType


class TestEventBase(unittest.TestCase):
    """Test base event classes and metadata."""
    
    def test_event_metadata_creation(self):
        """Test event metadata creation and serialization."""
        metadata = EventMetadata(
            event_id="test-123",
            correlation_id="corr-456",
            timestamp=datetime.utcnow(),
            event_version="1.0",
            source_service="test-service",
            actor="test-user"
        )
        
        self.assertEqual(metadata.event_id, "test-123")
        self.assertEqual(metadata.correlation_id, "corr-456")
        self.assertEqual(metadata.actor, "test-user")
        
        # Test serialization
        metadata_dict = metadata.to_dict()
        self.assertIn('timestamp', metadata_dict)
        self.assertIn('event_id', metadata_dict)
        
        # Test deserialization
        restored_metadata = EventMetadata.from_dict(metadata_dict)
        self.assertEqual(restored_metadata.event_id, metadata.event_id)
    
    def test_domain_event_creation(self):
        """Test domain event creation."""
        event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project",
            repository_url="https://github.com/test/repo",
            actor="test-user"
        )
        
        self.assertEqual(event.get_event_type(), "project.created")
        self.assertEqual(event.aggregate_id, "proj-123")
        self.assertEqual(event.aggregate_type, "project")
        self.assertEqual(event.name, "Test Project")
        
        # Test serialization
        event_dict = event.to_dict()
        self.assertEqual(event_dict['event_type'], "project.created")
        self.assertIn('metadata', event_dict)
        self.assertIn('payload', event_dict)
        
        payload = event_dict['payload']
        self.assertEqual(payload['name'], "Test Project")
        self.assertEqual(payload['repository_url'], "https://github.com/test/repo")
    
    def test_event_filter(self):
        """Test event filtering logic."""
        # Create test events
        project_event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project",
            actor="user1"
        )
        
        ai_event = AIRequestStartedEvent(
            request_id="req-456",
            model_type="gpt-4",
            prompt="Test prompt",
            actor="user2"
        )
        
        # Test event type filtering
        event_filter = EventFilter(event_types=["project.created"])
        self.assertTrue(event_filter.matches(project_event))
        self.assertFalse(event_filter.matches(ai_event))
        
        # Test aggregate type filtering
        aggregate_filter = EventFilter(aggregate_types=["project"])
        self.assertTrue(aggregate_filter.matches(project_event))
        self.assertFalse(aggregate_filter.matches(ai_event))
        
        # Test actor filtering
        actor_filter = EventFilter(actors=["user1"])
        self.assertTrue(actor_filter.matches(project_event))
        self.assertFalse(actor_filter.matches(ai_event))


class TestDomainEvents(unittest.TestCase):
    """Test domain event implementations."""
    
    def test_project_events(self):
        """Test project lifecycle events."""
        # Project created
        created_event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project",
            repository_url="https://github.com/test/repo"
        )
        self.assertEqual(created_event.get_event_type(), "project.created")
        
        # Project updated
        updated_event = ProjectUpdatedEvent(
            project_id="proj-123",
            changes={"name": "Updated Project", "status": "active"}
        )
        self.assertEqual(updated_event.get_event_type(), "project.updated")
        self.assertEqual(updated_event.changes["name"], "Updated Project")
        
        # Repository processing
        processing_event = RepositoryProcessingStartedEvent(
            project_id="proj-123",
            repository_url="https://github.com/test/repo",
            job_id="job-789"
        )
        self.assertEqual(processing_event.get_event_type(), "repository.processing.started")
        self.assertEqual(processing_event.job_id, "job-789")
    
    def test_ai_events(self):
        """Test AI interaction events."""
        ai_event = AIRequestStartedEvent(
            request_id="req-123",
            model_type="gpt-4",
            prompt="Generate code for authentication",
            context={"project_id": "proj-456"}
        )
        
        self.assertEqual(ai_event.get_event_type(), "ai.request.started")
        self.assertEqual(ai_event.model_type, "gpt-4")
        self.assertEqual(ai_event.context["project_id"], "proj-456")
    
    def test_build_events(self):
        """Test build and deployment events."""
        build_event = BuildStartedEvent(
            build_id="build-123",
            project_id="proj-456",
            branch="main",
            commit_hash="abc123def",
            build_type="production"
        )
        
        self.assertEqual(build_event.get_event_type(), "build.started")
        self.assertEqual(build_event.project_id, "proj-456")
        self.assertEqual(build_event.build_type, "production")
    
    def test_spec_events(self):
        """Test specification and task events."""
        idea_event = IdeaCreatedEvent(
            idea_id="idea-123",
            project_id="proj-456",
            content="Add user authentication system",
            tags=["auth", "security"]
        )
        
        self.assertEqual(idea_event.get_event_type(), "idea.created")
        self.assertEqual(idea_event.tags, ["auth", "security"])
        
        spec_event = SpecFrozenEvent(
            spec_id="spec-789",
            project_id="proj-456",
            requirements=[{"id": 1, "description": "User login"}],
            design_document="Authentication design document"
        )
        
        self.assertEqual(spec_event.get_event_type(), "spec.frozen")
        self.assertEqual(len(spec_event.requirements), 1)


class TestEventStore(unittest.TestCase):
    """Test event store functionality."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.event_store = EventStore(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test database."""
        os.unlink(self.temp_db.name)
    
    def test_append_and_retrieve_events(self):
        """Test storing and retrieving events."""
        # Create test event
        event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project",
            actor="test-user"
        )
        
        # Store event
        self.event_store.append_event(event)
        
        # Retrieve events
        events = self.event_store.get_events()
        self.assertEqual(len(events), 1)
        
        stored_event = events[0]
        self.assertEqual(stored_event['event_type'], "project.created")
        self.assertEqual(stored_event['aggregate_id'], "proj-123")
        self.assertEqual(stored_event['actor'], "test-user")
    
    def test_event_filtering(self):
        """Test event filtering in store."""
        # Create multiple events
        project_event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project",
            actor="user1"
        )
        
        ai_event = AIRequestStartedEvent(
            request_id="req-456",
            model_type="gpt-4",
            prompt="Test prompt",
            actor="user2"
        )
        
        # Store events
        self.event_store.append_events([project_event, ai_event])
        
        # Filter by event type
        event_filter = EventFilter(event_types=["project.created"])
        filtered_events = self.event_store.get_events(event_filter=event_filter)
        self.assertEqual(len(filtered_events), 1)
        self.assertEqual(filtered_events[0]['event_type'], "project.created")
        
        # Filter by actor
        actor_filter = EventFilter(actors=["user2"])
        actor_events = self.event_store.get_events(event_filter=actor_filter)
        self.assertEqual(len(actor_events), 1)
        self.assertEqual(actor_events[0]['actor'], "user2")
    
    def test_aggregate_events(self):
        """Test retrieving events by aggregate."""
        project_id = "proj-123"
        
        # Create multiple events for same project
        created_event = ProjectCreatedEvent(
            project_id=project_id,
            name="Test Project"
        )
        
        updated_event = ProjectUpdatedEvent(
            project_id=project_id,
            changes={"status": "active"}
        )
        
        # Store events
        self.event_store.append_events([created_event, updated_event])
        
        # Retrieve by aggregate
        aggregate_events = self.event_store.get_events_by_aggregate(
            project_id, "project"
        )
        
        self.assertEqual(len(aggregate_events), 2)
        self.assertEqual(aggregate_events[0]['event_type'], "project.created")
        self.assertEqual(aggregate_events[1]['event_type'], "project.updated")
    
    def test_event_statistics(self):
        """Test event statistics."""
        # Create various events
        events = [
            ProjectCreatedEvent(project_id="proj-1", name="Project 1"),
            ProjectCreatedEvent(project_id="proj-2", name="Project 2"),
            AIRequestStartedEvent(request_id="req-1", model_type="gpt-4", prompt="Test")
        ]
        
        self.event_store.append_events(events)
        
        stats = self.event_store.get_event_statistics()
        self.assertEqual(stats['total_events'], 3)
        self.assertEqual(stats['event_type_counts']['project.created'], 2)
        self.assertEqual(stats['event_type_counts']['ai.request.started'], 1)
        self.assertEqual(stats['unique_event_types'], 2)


class TestEventRouter(unittest.TestCase):
    """Test event routing and subscriptions."""
    
    def setUp(self):
        """Set up test router."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.event_store = EventStore(self.temp_db.name)
        self.event_router = EventRouter(self.event_store)
    
    def tearDown(self):
        """Clean up test database."""
        os.unlink(self.temp_db.name)
    
    def test_subscription_management(self):
        """Test subscription creation and management."""
        handler = Mock()
        event_filter = EventFilter(event_types=["project.created"])
        
        # Subscribe
        self.event_router.subscribe(
            subscription_id="test-sub",
            event_filter=event_filter,
            handler=handler
        )
        
        # Check subscription exists
        stats = self.event_router.get_subscription_stats()
        self.assertEqual(stats['total_subscriptions'], 1)
        self.assertEqual(stats['active_subscriptions'], 1)
        
        # Deactivate subscription
        self.event_router.deactivate_subscription("test-sub")
        stats = self.event_router.get_subscription_stats()
        self.assertEqual(stats['active_subscriptions'], 0)
        self.assertEqual(stats['inactive_subscriptions'], 1)
        
        # Remove subscription
        removed = self.event_router.unsubscribe("test-sub")
        self.assertTrue(removed)
        
        stats = self.event_router.get_subscription_stats()
        self.assertEqual(stats['total_subscriptions'], 0)
    
    def test_event_routing(self):
        """Test event routing to subscribers."""
        handler1 = Mock(return_value="handler1_result")
        handler2 = Mock(return_value="handler2_result")
        
        # Subscribe to project events
        self.event_router.subscribe(
            subscription_id="project-sub",
            event_filter=EventFilter(event_types=["project.created"]),
            handler=handler1
        )
        
        # Subscribe to all events
        self.event_router.subscribe(
            subscription_id="all-sub",
            event_filter=EventFilter(),  # No filters = match all
            handler=handler2
        )
        
        # Create and route event
        event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project"
        )
        
        results = self.event_router.route_event(event)
        
        # Check both handlers were called
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        
        # Check results
        self.assertEqual(len(results), 2)
        self.assertTrue(results["project-sub"]["success"])
        self.assertTrue(results["all-sub"]["success"])
    
    def test_subscription_filtering(self):
        """Test subscription filtering works correctly."""
        project_handler = Mock()
        ai_handler = Mock()
        
        # Subscribe to different event types
        self.event_router.subscribe(
            subscription_id="project-sub",
            event_filter=EventFilter(event_types=["project.created"]),
            handler=project_handler
        )
        
        self.event_router.subscribe(
            subscription_id="ai-sub",
            event_filter=EventFilter(event_types=["ai.request.started"]),
            handler=ai_handler
        )
        
        # Route project event
        project_event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project"
        )
        
        results = self.event_router.route_event(project_event)
        
        # Only project handler should be called
        project_handler.assert_called_once_with(project_event)
        ai_handler.assert_not_called()
        
        self.assertEqual(len(results), 1)
        self.assertIn("project-sub", results)


class TestEventBus(unittest.TestCase):
    """Test high-level event bus functionality."""
    
    def setUp(self):
        """Set up test event bus."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.event_bus = EventBus(EventStore(self.temp_db.name))
    
    def tearDown(self):
        """Clean up test database."""
        os.unlink(self.temp_db.name)
    
    def test_publish_and_subscribe(self):
        """Test publishing events and subscribing to them."""
        handler = Mock()
        
        # Subscribe to project events
        self.event_bus.subscribe(
            subscription_id="test-sub",
            event_types=["project.created"],
            handler=handler
        )
        
        # Publish event
        event = ProjectCreatedEvent(
            project_id="proj-123",
            name="Test Project"
        )
        
        result = self.event_bus.publish(event)
        
        # Check event was stored and routed
        self.assertTrue(result['stored'])
        self.assertEqual(result['event_type'], "project.created")
        self.assertIn('routing_results', result)
        
        # Check handler was called
        handler.assert_called_once_with(event)
        
        # Check event is in store
        events = self.event_bus.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['event_type'], "project.created")
    
    def test_batch_publishing(self):
        """Test batch event publishing."""
        handler = Mock()
        
        # Subscribe to all events
        self.event_bus.subscribe(
            subscription_id="batch-sub",
            handler=handler
        )
        
        # Create batch of events
        events = [
            ProjectCreatedEvent(project_id="proj-1", name="Project 1"),
            ProjectCreatedEvent(project_id="proj-2", name="Project 2"),
            AIRequestStartedEvent(request_id="req-1", model_type="gpt-4", prompt="Test")
        ]
        
        results = self.event_bus.publish_batch(events)
        
        # Check all events were processed
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertTrue(result['stored'])
        
        # Check handler was called for each event
        self.assertEqual(handler.call_count, 3)
        
        # Check events are in store
        stored_events = self.event_bus.get_events()
        self.assertEqual(len(stored_events), 3)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
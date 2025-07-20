"""
Example usage of the event-driven domain model and event system.
This demonstrates how to use the event system in practice.
"""

import time
from datetime import datetime
from typing import Any

from .base import BaseEvent
from .domain_events import (
    ProjectCreatedEvent, RepositoryProcessingStartedEvent, 
    RepositoryProcessingCompletedEvent, AIRequestStartedEvent,
    IdeaCreatedEvent, SpecFrozenEvent, TasksCreatedEvent
)
from .event_router import EventBus, SubscriptionType


def project_created_handler(event: BaseEvent) -> None:
    """Handler for project created events."""
    print(f"🎉 New project created: {event.name}")
    print(f"   Project ID: {event.aggregate_id}")
    if event.repository_url:
        print(f"   Repository: {event.repository_url}")


def repository_processing_handler(event: BaseEvent) -> None:
    """Handler for repository processing events."""
    if event.get_event_type() == "repository.processing.started":
        print(f"🔄 Started processing repository for project {event.aggregate_id}")
        print(f"   Job ID: {event.job_id}")
    elif event.get_event_type() == "repository.processing.completed":
        print(f"✅ Repository processing completed for project {event.aggregate_id}")
        print(f"   Processing time: {event.processing_time_seconds:.2f}s")
        print(f"   System map ID: {event.system_map_id}")


def ai_interaction_handler(event: BaseEvent) -> None:
    """Handler for AI interaction events."""
    print(f"🤖 AI request started: {event.model_type}")
    print(f"   Request ID: {event.aggregate_id}")
    print(f"   Prompt: {event.prompt[:50]}...")


def spec_workflow_handler(event: BaseEvent) -> None:
    """Handler for spec workflow events."""
    event_type = event.get_event_type()
    
    if event_type == "idea.created":
        print(f"💡 New idea captured for project {event.project_id}")
        print(f"   Content: {event.content[:100]}...")
        print(f"   Tags: {', '.join(event.tags)}")
    
    elif event_type == "spec.frozen":
        print(f"📋 Specification frozen for project {event.project_id}")
        print(f"   Spec ID: {event.aggregate_id}")
        print(f"   Requirements count: {len(event.requirements)}")
    
    elif event_type == "tasks.created":
        print(f"📝 Tasks created from spec {event.spec_id}")
        print(f"   Task count: {len(event.tasks)}")


def audit_handler(event: BaseEvent) -> None:
    """Audit handler that logs all events."""
    print(f"📊 AUDIT: {event.get_event_type()} at {event.metadata.timestamp}")
    print(f"   Event ID: {event.metadata.event_id}")
    print(f"   Actor: {event.metadata.actor or 'system'}")
    print(f"   Correlation ID: {event.metadata.correlation_id}")


def demonstrate_event_system():
    """Demonstrate the event system with a complete workflow."""
    print("🚀 Event System Demonstration")
    print("=" * 50)
    
    # Initialize event bus
    event_bus = EventBus()
    
    # Set up subscriptions
    print("\n📡 Setting up event subscriptions...")
    
    # Subscribe to project events
    event_bus.subscribe(
        subscription_id="project-monitor",
        event_types=["project.created"],
        handler=project_created_handler,
        subscription_type=SubscriptionType.SYNC
    )
    
    # Subscribe to repository processing events
    event_bus.subscribe(
        subscription_id="repo-processor",
        event_types=["repository.processing.started", "repository.processing.completed"],
        handler=repository_processing_handler,
        subscription_type=SubscriptionType.SYNC
    )
    
    # Subscribe to AI events
    event_bus.subscribe(
        subscription_id="ai-monitor",
        event_types=["ai.request.started"],
        handler=ai_interaction_handler,
        subscription_type=SubscriptionType.SYNC
    )
    
    # Subscribe to spec workflow events
    event_bus.subscribe(
        subscription_id="spec-workflow",
        event_types=["idea.created", "spec.frozen", "tasks.created"],
        handler=spec_workflow_handler,
        subscription_type=SubscriptionType.SYNC
    )
    
    # Subscribe to all events for audit
    event_bus.subscribe(
        subscription_id="audit-logger",
        handler=audit_handler,
        subscription_type=SubscriptionType.BACKGROUND
    )
    
    print("✅ Subscriptions configured")
    
    # Simulate a complete workflow
    print("\n🎬 Simulating software factory workflow...")
    
    # 1. Project creation
    print("\n--- Step 1: Project Creation ---")
    project_event = ProjectCreatedEvent(
        project_id="proj-demo-123",
        name="Demo Authentication System",
        repository_url="https://github.com/demo/auth-system",
        description="A demonstration authentication system",
        actor="developer@example.com"
    )
    
    result = event_bus.publish(project_event)
    print(f"Published event: {result['event_id']}")
    
    time.sleep(0.1)  # Small delay for demonstration
    
    # 2. Repository processing
    print("\n--- Step 2: Repository Processing ---")
    repo_start_event = RepositoryProcessingStartedEvent(
        project_id="proj-demo-123",
        repository_url="https://github.com/demo/auth-system",
        job_id="job-repo-456",
        correlation_id=project_event.metadata.correlation_id,
        actor="system"
    )
    
    event_bus.publish(repo_start_event)
    
    time.sleep(0.1)
    
    repo_complete_event = RepositoryProcessingCompletedEvent(
        project_id="proj-demo-123",
        job_id="job-repo-456",
        system_map_id="map-789",
        processing_time_seconds=15.7,
        correlation_id=project_event.metadata.correlation_id,
        actor="system"
    )
    
    event_bus.publish(repo_complete_event)
    
    # 3. Idea capture and spec workflow
    print("\n--- Step 3: Spec Workflow ---")
    idea_event = IdeaCreatedEvent(
        idea_id="idea-auth-001",
        project_id="proj-demo-123",
        content="Implement OAuth2 authentication with JWT tokens for secure API access",
        tags=["authentication", "oauth2", "jwt", "security"],
        correlation_id=project_event.metadata.correlation_id,
        actor="product-manager@example.com"
    )
    
    event_bus.publish(idea_event)
    
    time.sleep(0.1)
    
    spec_event = SpecFrozenEvent(
        spec_id="spec-auth-002",
        project_id="proj-demo-123",
        requirements=[
            {"id": 1, "description": "User registration and login"},
            {"id": 2, "description": "JWT token generation and validation"},
            {"id": 3, "description": "OAuth2 provider integration"}
        ],
        design_document="OAuth2 authentication system design with JWT tokens",
        correlation_id=project_event.metadata.correlation_id,
        actor="architect@example.com"
    )
    
    event_bus.publish(spec_event)
    
    time.sleep(0.1)
    
    tasks_event = TasksCreatedEvent(
        task_list_id="tasks-auth-003",
        spec_id="spec-auth-002",
        project_id="proj-demo-123",
        tasks=[
            {"id": 1, "title": "Implement user model and database schema"},
            {"id": 2, "title": "Create JWT token service"},
            {"id": 3, "title": "Build OAuth2 integration endpoints"},
            {"id": 4, "title": "Add authentication middleware"}
        ],
        correlation_id=project_event.metadata.correlation_id,
        actor="system"
    )
    
    event_bus.publish(tasks_event)
    
    # 4. AI interaction
    print("\n--- Step 4: AI Assistance ---")
    ai_event = AIRequestStartedEvent(
        request_id="ai-req-004",
        model_type="gpt-4",
        prompt="Generate Python code for JWT token validation middleware",
        context={
            "project_id": "proj-demo-123",
            "spec_id": "spec-auth-002",
            "task_id": 4
        },
        correlation_id=project_event.metadata.correlation_id,
        actor="developer@example.com"
    )
    
    event_bus.publish(ai_event)
    
    # Show system statistics
    print("\n📈 Event System Statistics")
    print("-" * 30)
    stats = event_bus.get_stats()
    
    print(f"Total events stored: {stats['event_store']['total_events']}")
    print(f"Event types: {stats['event_store']['unique_event_types']}")
    print(f"Active subscriptions: {stats['subscriptions']['active_subscriptions']}")
    
    print("\nEvent type breakdown:")
    for event_type, count in stats['event_store']['event_type_counts'].items():
        print(f"  {event_type}: {count}")
    
    # Show correlation tracking
    print(f"\n🔗 Correlation Tracking")
    print("-" * 25)
    correlation_id = project_event.metadata.correlation_id
    print(f"Correlation ID: {correlation_id}")
    
    # Get all events with same correlation ID
    correlated_events = event_bus.event_store.get_events_by_correlation(correlation_id)
    print(f"Related events: {len(correlated_events)}")
    
    for event in correlated_events:
        print(f"  - {event['event_type']} by {event['actor'] or 'system'}")
    
    print("\n✨ Event system demonstration completed!")


if __name__ == "__main__":
    demonstrate_event_system()
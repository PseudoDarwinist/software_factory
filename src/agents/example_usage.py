"""
Example usage of the intelligent agent framework.
"""

import time
import logging
from datetime import datetime

from .agent_manager import AgentManager
from ..events.event_router import EventBus
from ..events.event_store import EventStore
from ..events.domain_events import (
    SpecFrozenEvent, CodeChangedEvent, RepositoryProcessingCompletedEvent
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demonstrate_agent_framework():
    """Demonstrate the intelligent agent framework with event subscriptions."""
    
    print("🤖 Starting Intelligent Agent Framework Demo")
    print("=" * 50)
    
    # Create event infrastructure
    event_store = EventStore(":memory:")  # In-memory for demo
    event_bus = EventBus(event_store)
    
    # Create agent manager with default agents
    agent_manager = AgentManager.create_default_setup(event_bus)
    
    print("📋 Registered Agents:")
    for agent_id in agent_manager.agents.keys():
        print(f"  - {agent_id}")
    
    # Start all agents
    print("\n🚀 Starting all agents...")
    agent_manager.start_all_agents()
    
    # Wait a moment for agents to initialize
    time.sleep(1)
    
    print("\n📊 System Status:")
    status = agent_manager.get_system_status()
    for agent_id, agent_status in status['agents'].items():
        print(f"  - {agent_id}: {agent_status['status']}")
    
    print("\n🎯 Demonstrating Event-Driven Workflows:")
    
    # Scenario 1: Spec Frozen -> Tasks Created -> Planning (with Claude LLM calls)
    print("\n1️⃣ Spec Frozen Event (triggers Define Agent with Claude LLM -> Planner Agent)")
    spec_event = SpecFrozenEvent(
        spec_id="demo_spec_001",
        project_id="demo_project",
        requirements=[
            {
                "id": "req_1",
                "user_story": "As a user, I want to create and manage projects",
                "acceptance_criteria": [
                    "WHEN I click create project THEN a new project SHALL be created",
                    "WHEN I provide project details THEN they SHALL be saved"
                ]
            },
            {
                "id": "req_2", 
                "user_story": "As a developer, I want API endpoints for project management",
                "acceptance_criteria": [
                    "WHEN I call GET /projects THEN I SHALL receive a list of projects",
                    "WHEN I call POST /projects THEN a new project SHALL be created"
                ]
            }
        ],
        design_document="""
        # Project Management System Design
        
        ## Architecture
        - REST API backend with Flask
        - SQLite database for data persistence
        - React frontend for user interface
        
        ## Components
        - Project model with CRUD operations
        - API endpoints for project management
        - Frontend components for project listing and creation
        
        ## Data Models
        - Project: id, name, description, created_at, updated_at
        """
    )
    
    event_bus.publish(spec_event)
    print(f"   📤 Published spec.frozen event for spec: {spec_event.spec_id}")
    print(f"   🤖 Define Agent will call Claude to generate implementation tasks...")
    
    # Wait for agents to process (longer for LLM calls)
    time.sleep(5)
    
    # Scenario 2: Code Changed -> Build Triggered (with Claude code analysis)
    print("\n2️⃣ Code Changed Event (triggers Build Agent with Claude code analysis)")
    code_event = CodeChangedEvent(
        change_id="demo_change_001",
        project_id="demo_project",
        branch="feature/project-management",
        commit_hash="abc123def456",
        changed_files=[
            "src/models/project.py",
            "src/api/projects.py", 
            "tests/test_projects.py",
            "frontend/src/components/ProjectList.jsx"
        ],
        author="demo_developer"
    )
    
    event_bus.publish(code_event)
    print(f"   📤 Published code.changed event for project: {code_event.project_id}")
    print(f"   🤖 Build Agent will call Claude to analyze code changes and optimize build...")
    
    # Wait for agents to process (longer for LLM calls)
    time.sleep(5)
    
    # Scenario 3: Repository Processing Completed -> Initial Build
    print("\n3️⃣ Repository Processing Completed Event (triggers Build Agent)")
    repo_event = RepositoryProcessingCompletedEvent(
        project_id="demo_project",
        job_id="repo_job_001",
        system_map_id="system_map_001",
        processing_time_seconds=45.2
    )
    
    event_bus.publish(repo_event)
    print(f"   📤 Published repository.processing.completed event")
    
    # Wait for final processing
    time.sleep(3)
    
    # Show results
    print("\n📈 Processing Results:")
    
    # Get all events from the store
    all_events = event_bus.get_events()
    print(f"   📊 Total events processed: {len(all_events)}")
    
    # Group events by type
    event_types = {}
    for event in all_events:
        event_type = event['event_type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("   📋 Event types generated:")
    for event_type, count in event_types.items():
        print(f"      - {event_type}: {count}")
    
    # Show agent statistics
    print("\n📊 Agent Statistics:")
    final_status = agent_manager.get_system_status()
    for agent_id, agent_status in final_status['agents'].items():
        stats = agent_status.get('stats', {})
        print(f"   🤖 {agent_id}:")
        print(f"      - Events processed: {stats.get('events_processed', 0)}")
        print(f"      - Success rate: {stats.get('events_succeeded', 0)}/{stats.get('events_processed', 0)}")
        if stats.get('last_event_at'):
            print(f"      - Last activity: {stats['last_event_at']}")
    
    # Show coordination statistics
    manager_stats = final_status['manager_stats']
    print(f"\n🎛️  Coordination Statistics:")
    print(f"   - Agent interactions: {manager_stats.get('agent_interactions', 0)}")
    print(f"   - Events blocked by rules: {manager_stats.get('events_blocked_by_rules', 0)}")
    print(f"   - Infinite loops prevented: {manager_stats.get('infinite_loops_prevented', 0)}")
    
    # Show recent interactions
    interactions = agent_manager.get_agent_interactions(limit=10)
    if interactions:
        print(f"\n🔄 Recent Agent Interactions:")
        for interaction in interactions[-5:]:  # Show last 5
            timestamp = interaction['timestamp'].strftime("%H:%M:%S")
            print(f"   - {timestamp}: {interaction['source_agent']} -> {interaction['event_type']}")
    
    print("\n🛑 Stopping all agents...")
    agent_manager.stop_all_agents()
    
    print("\n✅ Demo completed successfully!")
    print("=" * 50)
    
    return {
        'total_events': len(all_events),
        'event_types': event_types,
        'agent_stats': {
            agent_id: agent_status.get('stats', {})
            for agent_id, agent_status in final_status['agents'].items()
        },
        'coordination_stats': manager_stats
    }


def demonstrate_loop_prevention():
    """Demonstrate infinite loop prevention capabilities."""
    
    print("\n🔄 Demonstrating Loop Prevention")
    print("=" * 40)
    
    # Create event infrastructure
    event_store = EventStore(":memory:")
    event_bus = EventBus(event_store)
    agent_manager = AgentManager.create_default_setup(event_bus)
    
    # Start agents
    agent_manager.start_all_agents()
    
    print("🚨 Simulating rapid event cascade (potential infinite loop)...")
    
    # Publish many similar events rapidly
    correlation_id = "loop_test_correlation"
    for i in range(20):
        spec_event = SpecFrozenEvent(
            spec_id=f"loop_spec_{i}",
            project_id="loop_project",
            requirements=[{"id": f"req_{i}", "user_story": f"Requirement {i}"}],
            design_document=f"Design {i}",
            correlation_id=correlation_id
        )
        event_bus.publish(spec_event)
        time.sleep(0.1)  # Small delay between events
    
    # Wait for processing
    time.sleep(3)
    
    # Check results
    status = agent_manager.get_system_status()
    manager_stats = status['manager_stats']
    
    print(f"📊 Loop Prevention Results:")
    print(f"   - Events blocked by rules: {manager_stats.get('events_blocked_by_rules', 0)}")
    print(f"   - Infinite loops prevented: {manager_stats.get('infinite_loops_prevented', 0)}")
    print(f"   - Total agent interactions: {manager_stats.get('agent_interactions', 0)}")
    
    # Show coordination rules in effect
    print(f"\n🛡️  Active Coordination Rules:")
    for rule_id, rule_info in status['coordination_rules'].items():
        if rule_info['enabled']:
            print(f"   - {rule_id}: max {rule_info['max_frequency_per_hour']}/hour, "
                  f"cooldown {rule_info['cooldown_seconds']}s")
    
    agent_manager.stop_all_agents()
    print("✅ Loop prevention demo completed!")


if __name__ == "__main__":
    # Run the main demonstration
    results = demonstrate_agent_framework()
    
    # Run loop prevention demonstration
    demonstrate_loop_prevention()
    
    print(f"\n🎉 All demonstrations completed successfully!")
    print(f"📊 Summary: {results['total_events']} events processed across {len(results['agent_stats'])} agents")
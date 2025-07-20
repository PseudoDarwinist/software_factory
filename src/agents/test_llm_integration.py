"""
Test LLM integration in agents.
"""

import logging
from datetime import datetime

from .define_agent import DefineAgent
from .build_agent import BuildAgent
from ..events.event_router import EventBus
from ..events.event_store import EventStore
from ..events.domain_events import SpecFrozenEvent, CodeChangedEvent
from ..services.ai_service import get_ai_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_define_agent_llm():
    """Test Define Agent LLM integration."""
    print("🧪 Testing Define Agent LLM Integration")
    print("=" * 40)
    
    # Create event infrastructure
    event_store = EventStore(":memory:")
    event_bus = EventBus(event_store)
    
    # Create Define Agent
    define_agent = DefineAgent(event_bus)
    define_agent.start()
    
    print("✅ Define Agent started")
    
    # Test AI service availability
    ai_service = get_ai_service()
    service_status = ai_service.get_service_status()
    
    print(f"🤖 AI Service Status:")
    print(f"   - Model Garden available: {service_status['model_garden']['available']}")
    print(f"   - Goose available: {service_status['goose']['available']}")
    
    # Create a simple spec to test LLM task generation
    spec_event = SpecFrozenEvent(
        spec_id="test_llm_spec",
        project_id="test_project",
        requirements=[
            {
                "id": "req_1",
                "user_story": "As a user, I want to manage tasks",
                "acceptance_criteria": [
                    "WHEN I create a task THEN it SHALL be saved",
                    "WHEN I list tasks THEN I SHALL see all my tasks"
                ]
            }
        ],
        design_document="""
        # Simple Task Management
        
        ## Components
        - Task model with CRUD operations
        - REST API for task management
        - Simple web interface
        """
    )
    
    print(f"\n📤 Publishing spec.frozen event...")
    event_bus.publish(spec_event)
    
    # Wait for processing
    import time
    time.sleep(3)
    
    # Check results
    events = event_bus.get_events()
    tasks_created_events = [e for e in events if e['event_type'] == 'tasks.created']
    
    if tasks_created_events:
        print(f"✅ Define Agent successfully generated {len(tasks_created_events)} tasks.created events")
        
        # Show some details from the first event
        first_event = tasks_created_events[0]
        payload = eval(first_event['payload'])  # Simple parsing for demo
        tasks = payload.get('tasks', [])
        print(f"   📋 Generated {len(tasks)} implementation tasks")
        
        if tasks:
            print(f"   🔍 Sample task: {tasks[0].get('title', 'No title')}")
    else:
        print("❌ No tasks.created events generated")
    
    define_agent.stop()
    print("🛑 Define Agent stopped")


def test_build_agent_llm():
    """Test Build Agent LLM integration."""
    print("\n🧪 Testing Build Agent LLM Integration")
    print("=" * 40)
    
    # Create event infrastructure
    event_store = EventStore(":memory:")
    event_bus = EventBus(event_store)
    
    # Create Build Agent
    build_agent = BuildAgent(event_bus)
    build_agent.start()
    
    print("✅ Build Agent started")
    
    # Create a code change event
    code_event = CodeChangedEvent(
        change_id="test_change",
        project_id="test_project",
        branch="main",
        commit_hash="test123",
        changed_files=[
            "src/models/task.py",
            "src/api/tasks.py",
            "tests/test_tasks.py"
        ],
        author="test_developer"
    )
    
    print(f"\n📤 Publishing code.changed event...")
    event_bus.publish(code_event)
    
    # Wait for processing
    import time
    time.sleep(5)  # Longer wait for build processing
    
    # Check results
    events = event_bus.get_events()
    build_events = [e for e in events if e['event_type'].startswith('build.')]
    
    if build_events:
        print(f"✅ Build Agent successfully generated {len(build_events)} build events")
        
        # Show build event types
        build_types = [e['event_type'] for e in build_events]
        print(f"   📋 Build events: {', '.join(set(build_types))}")
    else:
        print("❌ No build events generated")
    
    build_agent.stop()
    print("🛑 Build Agent stopped")


def test_ai_service_directly():
    """Test AI service directly to verify it's working."""
    print("\n🧪 Testing AI Service Directly")
    print("=" * 40)
    
    ai_service = get_ai_service()
    
    # Test simple prompt
    test_prompt = "Generate 3 simple implementation tasks for a basic todo application with a REST API."
    
    print(f"📝 Test prompt: {test_prompt}")
    
    # Try Model Garden first
    try:
        print("\n🔄 Testing Model Garden (Claude)...")
        result = ai_service.execute_model_garden_task(
            instruction=test_prompt,
            model='claude-sonnet-3.5',
            role='developer'
        )
        
        if result['success']:
            print("✅ Model Garden (Claude) working!")
            print(f"   📄 Response length: {len(result['output'])} characters")
            print(f"   🔍 Sample: {result['output'][:100]}...")
        else:
            print(f"❌ Model Garden failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Model Garden exception: {e}")
    
    # Try Goose as fallback
    try:
        print("\n🔄 Testing Goose...")
        result = ai_service.execute_goose_task(
            instruction=test_prompt,
            role='developer'
        )
        
        if result['success']:
            print("✅ Goose working!")
            print(f"   📄 Response length: {len(result['output'])} characters")
            print(f"   🔍 Sample: {result['output'][:100]}...")
        else:
            print(f"❌ Goose failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Goose exception: {e}")


if __name__ == "__main__":
    print("🚀 Starting LLM Integration Tests")
    print("=" * 50)
    
    # Test AI service directly first
    test_ai_service_directly()
    
    # Test agents with LLM integration
    test_define_agent_llm()
    test_build_agent_llm()
    
    print("\n🎉 LLM Integration Tests Completed!")
    print("=" * 50)
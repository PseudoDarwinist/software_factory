"""
Tests for the intelligent agent framework.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.agents.base import BaseAgent, AgentConfig, EventProcessingResult, AgentStatus
from src.agents.define_agent import DefineAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.build_agent import BuildAgent
from src.agents.agent_manager import AgentManager, AgentCoordinationRule
from src.events.base import BaseEvent, EventFilter
from src.events.domain_events import (
    SpecFrozenEvent, TasksCreatedEvent, CodeChangedEvent,
    RepositoryProcessingCompletedEvent, ProjectUpdatedEvent
)
from src.events.event_router import EventBus
from src.events.event_store import EventStore


class TestAgent(BaseAgent):
    """Test agent for testing base functionality."""
    
    def __init__(self, event_bus, agent_id="test_agent", event_types=None):
        config = AgentConfig(
            agent_id=agent_id,
            name="Test Agent",
            description="Agent for testing",
            event_types=event_types or ["test.event"],
            max_concurrent_events=2,
            timeout_seconds=5.0
        )
        super().__init__(config, event_bus)
        self.processed_events = []
        self.should_fail = False
        self.processing_delay = 0
    
    def process_event(self, event: BaseEvent) -> EventProcessingResult:
        """Process test events."""
        if self.processing_delay > 0:
            time.sleep(self.processing_delay)
        
        self.processed_events.append(event)
        
        if self.should_fail:
            raise Exception("Test agent failure")
        
        return EventProcessingResult(
            success=True,
            agent_id=self.config.agent_id,
            event_id=event.metadata.event_id,
            event_type=event.get_event_type(),
            processing_time_seconds=0.0,
            result_data={'processed': True}
        )


class TestEvent(BaseEvent):
    """Test event for testing."""
    
    def __init__(self, test_data="test", **kwargs):
        super().__init__(**kwargs)
        self.test_data = test_data
    
    def get_event_type(self) -> str:
        return "test.event"
    
    def get_version(self) -> str:
        return "1.0"
    
    def get_payload(self) -> dict:
        return {'test_data': self.test_data}


@pytest.fixture
def event_store():
    """Create test event store."""
    return EventStore(":memory:")


@pytest.fixture
def event_bus(event_store):
    """Create test event bus."""
    return EventBus(event_store)


@pytest.fixture
def test_agent(event_bus):
    """Create test agent."""
    return TestAgent(event_bus)


class TestBaseAgent:
    """Test base agent functionality."""
    
    def test_agent_initialization(self, event_bus):
        """Test agent initialization."""
        config = AgentConfig(
            agent_id="test_agent",
            name="Test Agent",
            description="Test description",
            event_types=["test.event"]
        )
        
        agent = TestAgent(event_bus, "test_agent", ["test.event"])
        
        assert agent.config.agent_id == "test_agent"
        assert agent.status == AgentStatus.STOPPED
        assert len(agent.processed_events) == 0
    
    def test_agent_start_stop(self, test_agent):
        """Test agent start and stop."""
        # Start agent
        test_agent.start()
        assert test_agent.status == AgentStatus.RUNNING
        
        # Stop agent
        test_agent.stop()
        assert test_agent.status == AgentStatus.STOPPED
    
    def test_agent_pause_resume(self, test_agent):
        """Test agent pause and resume."""
        test_agent.start()
        
        # Pause agent
        test_agent.pause()
        assert test_agent.status == AgentStatus.PAUSED
        
        # Resume agent
        test_agent.resume()
        assert test_agent.status == AgentStatus.RUNNING
        
        test_agent.stop()
    
    def test_event_processing(self, test_agent, event_bus):
        """Test event processing."""
        test_agent.start()
        
        # Create and publish test event
        test_event = TestEvent(test_data="hello")
        event_bus.publish(test_event)
        
        # Wait for processing
        time.sleep(0.5)
        
        # Check that event was processed
        assert len(test_agent.processed_events) == 1
        assert test_agent.processed_events[0].test_data == "hello"
        
        test_agent.stop()
    
    def test_event_processing_failure(self, test_agent, event_bus):
        """Test event processing failure handling."""
        test_agent.start()
        test_agent.should_fail = True
        
        # Create and publish test event
        test_event = TestEvent(test_data="fail")
        event_bus.publish(test_event)
        
        # Wait for processing
        time.sleep(0.5)
        
        # Check that event was attempted but failed
        assert len(test_agent.processed_events) == 1
        assert test_agent.stats['events_failed'] == 1
        
        test_agent.stop()
    
    def test_concurrent_event_processing(self, test_agent, event_bus):
        """Test concurrent event processing."""
        test_agent.start()
        test_agent.processing_delay = 0.2  # Add delay to test concurrency
        
        # Publish multiple events
        events = [TestEvent(test_data=f"event_{i}") for i in range(3)]
        for event in events:
            event_bus.publish(event)
        
        # Wait for processing
        time.sleep(1.0)
        
        # Check that all events were processed
        assert len(test_agent.processed_events) == 3
        
        test_agent.stop()
    
    def test_loop_detection(self, test_agent, event_bus):
        """Test infinite loop detection."""
        test_agent.start()
        
        # Publish many events with same correlation ID rapidly
        correlation_id = "test_correlation"
        for i in range(150):  # Exceed max_events_per_window
            event = TestEvent(test_data=f"loop_{i}", correlation_id=correlation_id)
            event_bus.publish(event)
        
        # Wait for processing
        time.sleep(1.0)
        
        # Should have processed some events but not all due to loop detection
        assert len(test_agent.processed_events) < 150
        
        test_agent.stop()
    
    def test_agent_statistics(self, test_agent, event_bus):
        """Test agent statistics tracking."""
        test_agent.start()
        
        # Process some events
        for i in range(5):
            event = TestEvent(test_data=f"stats_{i}")
            event_bus.publish(event)
        
        time.sleep(0.5)
        
        # Check statistics
        status = test_agent.get_status()
        assert status['stats']['events_processed'] == 5
        assert status['stats']['events_succeeded'] == 5
        assert status['stats']['events_failed'] == 0
        
        test_agent.stop()


class TestDefineAgent:
    """Test Define Agent functionality."""
    
    def test_define_agent_initialization(self, event_bus):
        """Test Define Agent initialization."""
        agent = DefineAgent(event_bus)
        
        assert agent.config.agent_id == "define_agent"
        assert "spec.frozen" in agent.config.event_types
    
    def test_spec_frozen_processing(self, event_bus):
        """Test processing of spec.frozen events."""
        agent = DefineAgent(event_bus)
        agent.start()
        
        # Create spec.frozen event
        spec_event = SpecFrozenEvent(
            spec_id="test_spec",
            project_id="test_project",
            requirements=[
                {
                    "id": "req_1",
                    "user_story": "As a user, I want to create projects",
                    "acceptance_criteria": ["WHEN I click create THEN project SHALL be created"]
                }
            ],
            design_document="Test design document"
        )
        
        event_bus.publish(spec_event)
        time.sleep(1.0)
        
        # Check that tasks.created event was generated
        events = event_bus.get_events()
        tasks_created_events = [e for e in events if e['event_type'] == 'tasks.created']
        assert len(tasks_created_events) > 0
        
        agent.stop()
    
    def test_rule_based_task_generation(self, event_bus):
        """Test rule-based task generation."""
        agent = DefineAgent(event_bus)
        
        requirements = [
            {
                "id": "req_1",
                "user_story": "As a user, I want database functionality",
                "acceptance_criteria": ["Database should store data"]
            },
            {
                "id": "req_2", 
                "user_story": "As a user, I want API endpoints",
                "acceptance_criteria": ["API should respond to requests"]
            }
        ]
        
        tasks = agent._generate_tasks_rule_based(
            spec_id="test_spec",
            project_id="test_project",
            requirements=requirements,
            design_document="Test design"
        )
        
        assert len(tasks) > 0
        
        # Should have database and API tasks
        task_types = [task['type'] for task in tasks]
        assert 'database' in task_types
        assert 'api' in task_types


class TestPlannerAgent:
    """Test Planner Agent functionality."""
    
    def test_planner_agent_initialization(self, event_bus):
        """Test Planner Agent initialization."""
        agent = PlannerAgent(event_bus)
        
        assert agent.config.agent_id == "planner_agent"
        assert "tasks.created" in agent.config.event_types
    
    def test_tasks_created_processing(self, event_bus):
        """Test processing of tasks.created events."""
        agent = PlannerAgent(event_bus)
        agent.start()
        
        # Create tasks.created event
        tasks = [
            {
                "id": "task_1",
                "title": "Create database",
                "type": "database",
                "priority": "high",
                "estimated_hours": 8,
                "dependencies": []
            },
            {
                "id": "task_2",
                "title": "Create API",
                "type": "api",
                "priority": "medium",
                "estimated_hours": 6,
                "dependencies": ["task_1"]
            }
        ]
        
        tasks_event = TasksCreatedEvent(
            task_list_id="test_tasks",
            spec_id="test_spec",
            project_id="test_project",
            tasks=tasks
        )
        
        event_bus.publish(tasks_event)
        time.sleep(1.0)
        
        # Check that project.updated event was generated
        events = event_bus.get_events()
        project_updated_events = [e for e in events if e['event_type'] == 'project.updated']
        assert len(project_updated_events) > 0
        
        agent.stop()
    
    def test_dependency_analysis(self, event_bus):
        """Test task dependency analysis."""
        agent = PlannerAgent(event_bus)
        
        tasks = [
            {"id": "task_1", "dependencies": []},
            {"id": "task_2", "dependencies": ["task_1"]},
            {"id": "task_3", "dependencies": ["task_2"]},
            {"id": "task_4", "dependencies": ["task_1"]}  # Parallel to task_2
        ]
        
        analysis = agent._analyze_dependencies(tasks)
        
        assert len(analysis['dependency_graph']) == 4
        assert analysis['dependency_graph']['task_2'] == ['task_1']
        assert analysis['dependency_graph']['task_3'] == ['task_2']
        assert len(analysis['circular_dependencies']) == 0
    
    def test_timeline_estimation(self, event_bus):
        """Test timeline estimation."""
        agent = PlannerAgent(event_bus)
        
        tasks = [
            {"id": "task_1", "estimated_hours": 4, "dependencies": []},
            {"id": "task_2", "estimated_hours": 6, "dependencies": ["task_1"]},
            {"id": "task_3", "estimated_hours": 2, "dependencies": ["task_1"]}
        ]
        
        dependency_analysis = agent._analyze_dependencies(tasks)
        timeline = agent._estimate_timeline(tasks, dependency_analysis)
        
        assert timeline['total_hours'] == 12
        assert timeline['max_finish_time'] == 10  # task_1(4) + task_2(6)
        assert timeline['parallelization_factor'] > 1  # task_2 and task_3 can run in parallel


class TestBuildAgent:
    """Test Build Agent functionality."""
    
    def test_build_agent_initialization(self, event_bus):
        """Test Build Agent initialization."""
        agent = BuildAgent(event_bus)
        
        assert agent.config.agent_id == "build_agent"
        assert "code.changed" in agent.config.event_types
        assert "repository.processing.completed" in agent.config.event_types
    
    def test_code_changed_processing(self, event_bus):
        """Test processing of code.changed events."""
        agent = BuildAgent(event_bus)
        agent.start()
        
        # Create code.changed event
        code_event = CodeChangedEvent(
            change_id="test_change",
            project_id="test_project",
            branch="main",
            commit_hash="abc123",
            changed_files=["src/main.py", "tests/test_main.py"],
            author="test_user"
        )
        
        event_bus.publish(code_event)
        time.sleep(2.0)  # Build takes time
        
        # Check that build events were generated
        events = event_bus.get_events()
        build_started_events = [e for e in events if e['event_type'] == 'build.started']
        assert len(build_started_events) > 0
        
        agent.stop()
    
    def test_build_type_determination(self, event_bus):
        """Test build type determination based on changed files."""
        agent = BuildAgent(event_bus)
        
        # Backend changes
        backend_files = ["src/main.py", "requirements.txt"]
        build_type = agent._determine_build_type(backend_files)
        assert build_type in ["backend", "full"]
        
        # Frontend changes
        frontend_files = ["frontend/app.js", "frontend/style.css"]
        build_type = agent._determine_build_type(frontend_files)
        assert build_type == "frontend"
        
        # Test changes
        test_files = ["tests/test_main.py"]
        build_type = agent._determine_build_type(test_files)
        assert build_type == "test"
    
    def test_repository_completed_processing(self, event_bus):
        """Test processing of repository.processing.completed events."""
        agent = BuildAgent(event_bus)
        agent.start()
        
        # Create repository.processing.completed event
        repo_event = RepositoryProcessingCompletedEvent(
            project_id="test_project",
            job_id="test_job",
            system_map_id="test_map",
            processing_time_seconds=30.0
        )
        
        event_bus.publish(repo_event)
        time.sleep(2.0)
        
        # Check that build was triggered
        events = event_bus.get_events()
        build_events = [e for e in events if e['event_type'].startswith('build.')]
        assert len(build_events) > 0
        
        agent.stop()


class TestAgentManager:
    """Test Agent Manager functionality."""
    
    def test_agent_manager_initialization(self, event_bus):
        """Test Agent Manager initialization."""
        manager = AgentManager(event_bus)
        
        assert len(manager.agents) == 0
        assert len(manager.coordination_rules) > 0  # Default rules
        assert manager.loop_detection_enabled is True
    
    def test_agent_registration(self, event_bus):
        """Test agent registration and unregistration."""
        manager = AgentManager(event_bus)
        test_agent = TestAgent(event_bus)
        
        # Register agent
        manager.register_agent(test_agent)
        assert "test_agent" in manager.agents
        
        # Unregister agent
        result = manager.unregister_agent("test_agent")
        assert result is True
        assert "test_agent" not in manager.agents
    
    def test_start_stop_all_agents(self, event_bus):
        """Test starting and stopping all agents."""
        manager = AgentManager(event_bus)
        
        # Register test agents
        agent1 = TestAgent(event_bus, "agent1")
        agent2 = TestAgent(event_bus, "agent2")
        manager.register_agent(agent1)
        manager.register_agent(agent2)
        
        # Start all agents
        manager.start_all_agents()
        assert agent1.status == AgentStatus.RUNNING
        assert agent2.status == AgentStatus.RUNNING
        
        # Stop all agents
        manager.stop_all_agents()
        assert agent1.status == AgentStatus.STOPPED
        assert agent2.status == AgentStatus.STOPPED
    
    def test_coordination_rules(self, event_bus):
        """Test coordination rules."""
        manager = AgentManager(event_bus)
        
        # Add custom rule
        rule = AgentCoordinationRule(
            rule_id="test_rule",
            description="Test rule",
            source_agent="test_agent",
            target_agent="*",
            event_type="test.event",
            max_frequency_per_hour=2,
            cooldown_seconds=5
        )
        
        manager.add_coordination_rule(rule)
        assert "test_rule" in manager.coordination_rules
        
        # Test event frequency limiting
        test_event = TestEvent()
        
        # First event should be allowed
        allowed = manager.check_event_allowed(test_event, "test_agent")
        assert allowed is True
        
        # Second event should be allowed
        allowed = manager.check_event_allowed(test_event, "test_agent")
        assert allowed is True
        
        # Third event should be blocked (exceeds max_frequency_per_hour)
        allowed = manager.check_event_allowed(test_event, "test_agent")
        assert allowed is False
    
    def test_infinite_loop_detection(self, event_bus):
        """Test infinite loop detection."""
        manager = AgentManager(event_bus)
        
        # Simulate rapid event cascade
        correlation_id = "test_correlation"
        for i in range(10):
            event = TestEvent(correlation_id=correlation_id)
            manager._record_agent_interaction(event, f"agent_{i % 2}")  # Alternate between 2 agents
        
        # Next event should be detected as potential loop
        test_event = TestEvent(correlation_id=correlation_id)
        is_loop = manager._detect_potential_infinite_loop(test_event, "agent_0")
        
        # With rapid alternating pattern, should detect potential loop
        assert len(manager.agent_interaction_history) > 0
    
    def test_default_agent_setup(self, event_bus):
        """Test default agent setup."""
        manager = AgentManager.create_default_setup(event_bus)
        
        assert len(manager.agents) == 3
        assert "define_agent" in manager.agents
        assert "planner_agent" in manager.agents
        assert "build_agent" in manager.agents
    
    def test_system_status(self, event_bus):
        """Test system status reporting."""
        manager = AgentManager(event_bus)
        test_agent = TestAgent(event_bus)
        manager.register_agent(test_agent)
        
        status = manager.get_system_status()
        
        assert 'manager_stats' in status
        assert 'agents' in status
        assert 'coordination_rules' in status
        assert 'test_agent' in status['agents']
    
    def test_pause_resume_agent(self, event_bus):
        """Test pausing and resuming specific agents."""
        manager = AgentManager(event_bus)
        test_agent = TestAgent(event_bus)
        manager.register_agent(test_agent)
        
        test_agent.start()
        
        # Pause agent
        result = manager.pause_agent("test_agent")
        assert result is True
        assert test_agent.status == AgentStatus.PAUSED
        
        # Resume agent
        result = manager.resume_agent("test_agent")
        assert result is True
        assert test_agent.status == AgentStatus.RUNNING
        
        test_agent.stop()


class TestAgentIntegration:
    """Test agent integration and coordination."""
    
    def test_define_to_planner_workflow(self, event_bus):
        """Test workflow from Define Agent to Planner Agent."""
        # Create agents
        define_agent = DefineAgent(event_bus)
        planner_agent = PlannerAgent(event_bus)
        
        define_agent.start()
        planner_agent.start()
        
        # Create spec.frozen event
        spec_event = SpecFrozenEvent(
            spec_id="integration_spec",
            project_id="integration_project",
            requirements=[
                {
                    "id": "req_1",
                    "user_story": "As a user, I want database functionality",
                    "acceptance_criteria": ["Database should store data"]
                }
            ],
            design_document="Integration test design"
        )
        
        event_bus.publish(spec_event)
        time.sleep(2.0)  # Allow processing
        
        # Check that both agents processed events
        events = event_bus.get_events()
        
        # Should have tasks.created event from DefineAgent
        tasks_created_events = [e for e in events if e['event_type'] == 'tasks.created']
        assert len(tasks_created_events) > 0
        
        # Should have project.updated event from PlannerAgent
        project_updated_events = [e for e in events if e['event_type'] == 'project.updated']
        assert len(project_updated_events) > 0
        
        define_agent.stop()
        planner_agent.stop()
    
    def test_agent_manager_coordination(self, event_bus):
        """Test agent manager coordinating multiple agents."""
        manager = AgentManager.create_default_setup(event_bus)
        manager.start_all_agents()
        
        # Publish events that should trigger agent cascade
        spec_event = SpecFrozenEvent(
            spec_id="manager_test_spec",
            project_id="manager_test_project",
            requirements=[{"id": "req_1", "user_story": "Test requirement"}],
            design_document="Test design"
        )
        
        code_event = CodeChangedEvent(
            change_id="manager_test_change",
            project_id="manager_test_project",
            branch="main",
            commit_hash="test123",
            changed_files=["src/test.py"],
            author="test_user"
        )
        
        event_bus.publish(spec_event)
        event_bus.publish(code_event)
        
        time.sleep(3.0)  # Allow processing
        
        # Check system status
        status = manager.get_system_status()
        
        # All agents should have processed some events
        for agent_id in ["define_agent", "planner_agent", "build_agent"]:
            agent_stats = status['agents'][agent_id]['stats']
            # At least one agent should have processed events
        
        # Should have coordination statistics
        assert status['manager_stats']['agent_interactions'] > 0
        
        manager.stop_all_agents()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
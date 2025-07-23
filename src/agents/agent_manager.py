"""
Agent Manager - Coordinates agents and prevents infinite event loops.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

try:
    from .base import BaseAgent, AgentStatus
    from ..events.base import BaseEvent
    from ..events.event_router import EventBus
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from agents.base import BaseAgent, AgentStatus
    from events.base import BaseEvent
    from events.event_router import EventBus


logger = logging.getLogger(__name__)


@dataclass
class AgentCoordinationRule:
    """Rule for coordinating agent interactions."""
    
    rule_id: str
    description: str
    source_agent: str
    target_agent: str
    event_type: str
    max_frequency_per_hour: int = 10
    cooldown_seconds: int = 60
    enabled: bool = True


class AgentManager:
    """Manages multiple agents and coordinates their interactions."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.agents: Dict[str, BaseAgent] = {}
        self.coordination_rules: Dict[str, AgentCoordinationRule] = {}
        self.event_frequency_tracker: Dict[str, List[datetime]] = defaultdict(list)
        self.agent_interaction_history: List[Dict[str, Any]] = []
        self.loop_detection_enabled = True
        self.max_cascade_depth = 5
        self._lock = threading.RLock()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            'total_events_processed': 0,
            'events_blocked_by_rules': 0,
            'infinite_loops_prevented': 0,
            'agent_interactions': 0,
            'started_at': None
        }
        
        # Initialize default coordination rules
        self._setup_default_coordination_rules()
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager."""
        with self._lock:
            agent_id = agent.config.agent_id
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} is already registered")
                return
            
            self.agents[agent_id] = agent
            logger.info(f"Registered agent: {agent_id}")
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        with self._lock:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if agent.status == AgentStatus.RUNNING:
                    agent.stop()
                del self.agents[agent_id]
                logger.info(f"Unregistered agent: {agent_id}")
                return True
            return False
    
    def start_all_agents(self) -> None:
        """Start all registered agents."""
        with self._lock:
            logger.info("Starting all agents")
            
            for agent_id, agent in self.agents.items():
                try:
                    if agent.status == AgentStatus.STOPPED:
                        agent.start()
                        logger.info(f"Started agent: {agent_id}")
                except Exception as e:
                    logger.error(f"Failed to start agent {agent_id}: {e}")
            
            # Start monitoring thread
            if not self._monitoring_thread or not self._monitoring_thread.is_alive():
                self._monitoring_thread = threading.Thread(
                    target=self._monitoring_loop,
                    name="AgentManagerMonitoring"
                )
                self._monitoring_thread.daemon = True
                self._monitoring_thread.start()
            
            self.stats['started_at'] = datetime.utcnow()
    
    def stop_all_agents(self) -> None:
        """Stop all registered agents."""
        with self._lock:
            logger.info("Stopping all agents")
            
            # Signal shutdown
            self._shutdown_event.set()
            
            for agent_id, agent in self.agents.items():
                try:
                    if agent.status == AgentStatus.RUNNING:
                        agent.stop()
                        logger.info(f"Stopped agent: {agent_id}")
                except Exception as e:
                    logger.error(f"Failed to stop agent {agent_id}: {e}")
            
            # Wait for monitoring thread to finish
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=10)
    
    def pause_agent(self, agent_id: str) -> bool:
        """Pause a specific agent."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].pause()
                logger.info(f"Paused agent: {agent_id}")
                return True
            return False
    
    def resume_agent(self, agent_id: str) -> bool:
        """Resume a specific agent."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].resume()
                logger.info(f"Resumed agent: {agent_id}")
                return True
            return False
    
    def add_coordination_rule(self, rule: AgentCoordinationRule) -> None:
        """Add a coordination rule."""
        with self._lock:
            self.coordination_rules[rule.rule_id] = rule
            logger.info(f"Added coordination rule: {rule.rule_id}")
    
    def remove_coordination_rule(self, rule_id: str) -> bool:
        """Remove a coordination rule."""
        with self._lock:
            if rule_id in self.coordination_rules:
                del self.coordination_rules[rule_id]
                logger.info(f"Removed coordination rule: {rule_id}")
                return True
            return False
    
    def check_event_allowed(self, event: BaseEvent, source_agent_id: str) -> bool:
        """Check if an event should be allowed based on coordination rules."""
        if not self.loop_detection_enabled:
            return True
        
        current_time = datetime.utcnow()
        event_type = event.get_event_type()
        
        # Check frequency limits
        frequency_key = f"{source_agent_id}:{event_type}"
        event_times = self.event_frequency_tracker[frequency_key]
        
        # Remove old events (older than 1 hour)
        hour_ago = current_time - timedelta(hours=1)
        event_times[:] = [t for t in event_times if t > hour_ago]
        
        # Check applicable coordination rules
        for rule in self.coordination_rules.values():
            if not rule.enabled:
                continue
            
            if (rule.source_agent == source_agent_id and 
                rule.event_type == event_type):
                
                # Check frequency limit
                if len(event_times) >= rule.max_frequency_per_hour:
                    logger.warning(f"Event blocked by frequency rule: {rule.rule_id}")
                    self.stats['events_blocked_by_rules'] += 1
                    return False
                
                # Check cooldown
                if event_times:
                    last_event_time = max(event_times)
                    cooldown_end = last_event_time + timedelta(seconds=rule.cooldown_seconds)
                    if current_time < cooldown_end:
                        logger.warning(f"Event blocked by cooldown rule: {rule.rule_id}")
                        self.stats['events_blocked_by_rules'] += 1
                        return False
        
        # Check for potential infinite loops
        if self._detect_potential_infinite_loop(event, source_agent_id):
            logger.warning(f"Event blocked to prevent infinite loop")
            self.stats['infinite_loops_prevented'] += 1
            return False
        
        # Event is allowed, record it
        event_times.append(current_time)
        self._record_agent_interaction(event, source_agent_id)
        
        return True
    
    def _detect_potential_infinite_loop(self, event: BaseEvent, source_agent_id: str) -> bool:
        """Detect potential infinite loops in agent interactions."""
        current_time = datetime.utcnow()
        correlation_id = event.metadata.correlation_id
        event_type = event.get_event_type()
        
        # Look at recent interactions for this correlation ID
        recent_interactions = [
            interaction for interaction in self.agent_interaction_history[-100:]
            if (interaction['correlation_id'] == correlation_id and
                interaction['timestamp'] > current_time - timedelta(minutes=10))
        ]
        
        if not recent_interactions:
            return False
        
        # Check for cascading events (A -> B -> C -> A)
        cascade_chain = []
        for interaction in recent_interactions:
            if interaction['event_type'] == event_type:
                cascade_chain.append(interaction['source_agent'])
        
        # If we see the same agent appearing multiple times in a short cascade
        if len(cascade_chain) > self.max_cascade_depth:
            return True
        
        # Check for rapid back-and-forth between agents
        agent_sequence = [i['source_agent'] for i in recent_interactions[-10:]]
        if len(agent_sequence) >= 6:
            # Look for patterns like A-B-A-B-A-B
            pattern_length = 2
            for i in range(len(agent_sequence) - pattern_length * 3):
                pattern = agent_sequence[i:i + pattern_length]
                if (agent_sequence[i + pattern_length:i + pattern_length * 2] == pattern and
                    agent_sequence[i + pattern_length * 2:i + pattern_length * 3] == pattern):
                    return True
        
        return False
    
    def _record_agent_interaction(self, event: BaseEvent, source_agent_id: str) -> None:
        """Record an agent interaction for loop detection."""
        interaction = {
            'timestamp': datetime.utcnow(),
            'source_agent': source_agent_id,
            'event_type': event.get_event_type(),
            'event_id': event.metadata.event_id,
            'correlation_id': event.metadata.correlation_id,
            'trace_id': event.metadata.trace_id
        }
        
        self.agent_interaction_history.append(interaction)
        
        # Limit history size
        if len(self.agent_interaction_history) > 1000:
            self.agent_interaction_history = self.agent_interaction_history[-500:]
        
        self.stats['agent_interactions'] += 1
    
    def _setup_default_coordination_rules(self) -> None:
        """Set up default coordination rules."""
        rules = [
            AgentCoordinationRule(
                rule_id="define_agent_spec_frozen_limit",
                description="Limit DefineAgent processing of spec.frozen events",
                source_agent="define_agent",
                target_agent="*",
                event_type="spec.frozen",
                max_frequency_per_hour=5,
                cooldown_seconds=300  # 5 minutes
            ),
            AgentCoordinationRule(
                rule_id="planner_agent_tasks_created_limit",
                description="Limit PlannerAgent processing of tasks.created events",
                source_agent="planner_agent",
                target_agent="*",
                event_type="tasks.created",
                max_frequency_per_hour=10,
                cooldown_seconds=60  # 1 minute
            ),
            AgentCoordinationRule(
                rule_id="build_agent_code_changed_limit",
                description="Limit BuildAgent processing of code.changed events",
                source_agent="build_agent",
                target_agent="*",
                event_type="code.changed",
                max_frequency_per_hour=20,
                cooldown_seconds=30  # 30 seconds
            ),
            AgentCoordinationRule(
                rule_id="general_event_cascade_limit",
                description="General limit to prevent event cascades",
                source_agent="*",
                target_agent="*",
                event_type="*",
                max_frequency_per_hour=100,
                cooldown_seconds=1
            )
        ]
        
        for rule in rules:
            self.coordination_rules[rule.rule_id] = rule
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        logger.info("Agent manager monitoring started")
        
        while not self._shutdown_event.is_set():
            try:
                self._perform_health_checks()
                self._cleanup_old_data()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
        
        logger.info("Agent manager monitoring stopped")
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all agents."""
        with self._lock:
            for agent_id, agent in self.agents.items():
                try:
                    status = agent.get_status()
                    if status['status'] == 'error':
                        logger.warning(f"Agent {agent_id} is in error state")
                        # Could implement auto-restart logic here
                    
                    # Check for stuck agents (no recent activity)
                    if status['stats']['last_event_at']:
                        last_event = datetime.fromisoformat(status['stats']['last_event_at'])
                        if datetime.utcnow() - last_event > timedelta(hours=1):
                            logger.info(f"Agent {agent_id} has been idle for over 1 hour")
                
                except Exception as e:
                    logger.error(f"Health check failed for agent {agent_id}: {e}")
    
    def _cleanup_old_data(self) -> None:
        """Clean up old tracking data."""
        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(hours=24)
        
        # Clean up frequency tracker
        for key in list(self.event_frequency_tracker.keys()):
            event_times = self.event_frequency_tracker[key]
            event_times[:] = [t for t in event_times if t > cutoff_time]
            if not event_times:
                del self.event_frequency_tracker[key]
        
        # Clean up interaction history
        self.agent_interaction_history[:] = [
            interaction for interaction in self.agent_interaction_history
            if interaction['timestamp'] > cutoff_time
        ]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        with self._lock:
            agent_statuses = {}
            for agent_id, agent in self.agents.items():
                try:
                    agent_statuses[agent_id] = agent.get_status()
                except Exception as e:
                    agent_statuses[agent_id] = {
                        'status': 'error',
                        'error': str(e)
                    }
            
            return {
                'manager_stats': self.stats.copy(),
                'agents': agent_statuses,
                'coordination_rules': {
                    rule_id: {
                        'description': rule.description,
                        'enabled': rule.enabled,
                        'max_frequency_per_hour': rule.max_frequency_per_hour,
                        'cooldown_seconds': rule.cooldown_seconds
                    }
                    for rule_id, rule in self.coordination_rules.items()
                },
                'loop_detection_enabled': self.loop_detection_enabled,
                'recent_interactions': len(self.agent_interaction_history),
                'active_frequency_trackers': len(self.event_frequency_tracker)
            }
    
    def get_agent_interactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent agent interactions."""
        with self._lock:
            return self.agent_interaction_history[-limit:] if self.agent_interaction_history else []
    
    def clear_interaction_history(self) -> int:
        """Clear interaction history and return count of cleared items."""
        with self._lock:
            count = len(self.agent_interaction_history)
            self.agent_interaction_history.clear()
            self.event_frequency_tracker.clear()
            return count
    
    def enable_loop_detection(self) -> None:
        """Enable loop detection."""
        self.loop_detection_enabled = True
        logger.info("Loop detection enabled")
    
    def disable_loop_detection(self) -> None:
        """Disable loop detection (use with caution)."""
        self.loop_detection_enabled = False
        logger.warning("Loop detection disabled - use with caution!")
    
    @classmethod
    def create_default_setup(cls, event_bus: EventBus, ai_broker=None) -> 'AgentManager':
        """Create agent manager with default agents."""
        manager = cls(event_bus)
        
        # Import agents here to avoid circular imports
        try:
            from .define_agent import create_define_agent
            from .capture_agent import create_capture_agent
        except ImportError:
            from define_agent import create_define_agent
            from capture_agent import create_capture_agent
        
        # Create and register available agents
        if ai_broker:
            define_agent = create_define_agent(event_bus, ai_broker)
            manager.register_agent(define_agent)
            
            capture_agent = create_capture_agent(event_bus, ai_broker)
            manager.register_agent(capture_agent)
        
        logger.info("Created agent manager with available agents")
        return manager
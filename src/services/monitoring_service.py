"""
Monitoring Service - Real-time system monitoring with event subscription and WebSocket streaming.
Collects metrics from events, agents, system health, and integrations for the dashboard.
"""

import json
import logging
import threading
import time
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

try:
    from ..core.events import Event, EventType
    from ..events.base import BaseEvent
    from ..models.base import db
    from ..models.event_log import EventLog
    from ..models.monitoring_metrics import MonitoringMetrics, AgentStatus, SystemHealth as SystemHealthModel
    from ..services.event_bus import get_event_bus
    from ..services.metrics_service import get_metrics_service
    from ..services.websocket_server import WebSocketServer
except ImportError:
    from core.events import Event, EventType
    from events.base import BaseEvent
    from models.base import db
    from models.event_log import EventLog
    from models.monitoring_metrics import MonitoringMetrics, AgentStatus, SystemHealth as SystemHealthModel
    from services.event_bus import get_event_bus
    from services.metrics_service import get_metrics_service
    from services.websocket_server import WebSocketServer

logger = logging.getLogger(__name__)


@dataclass
class EventMetrics:
    """Event metrics data structure."""
    total_events: int = 0
    events_per_minute: float = 0.0
    events_by_type: Dict[str, int] = None
    average_processing_time: float = 0.0
    error_rate: float = 0.0
    recent_events: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.events_by_type is None:
            self.events_by_type = {}
        if self.recent_events is None:
            self.recent_events = []


@dataclass
class AgentMetrics:
    """Agent metrics data structure."""
    agent_id: str
    status: str = "unknown"
    events_processed: int = 0
    success_rate: float = 0.0
    average_processing_time: float = 0.0
    current_load: int = 0
    last_activity: Optional[datetime] = None
    heartbeat_status: str = "unknown"  # green, yellow, red
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.last_activity:
            data['last_activity'] = self.last_activity.isoformat()
        return data


@dataclass
class SystemHealth:
    """System health data structure."""
    overall_score: float = 0.0
    components: Dict[str, Dict[str, Any]] = None
    resources: Dict[str, float] = None
    performance: Dict[str, float] = None
    
    def __post_init__(self):
        if self.components is None:
            self.components = {}
        if self.resources is None:
            self.resources = {}
        if self.performance is None:
            self.performance = {}


@dataclass
class IntegrationStatus:
    """Integration status data structure."""
    integrations: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.integrations is None:
            self.integrations = {}


class MonitoringService:
    """
    Real-time monitoring service that collects metrics from events, agents, and system components.
    Provides WebSocket streaming for dashboard updates and historical data storage.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", websocket_server: Optional[WebSocketServer] = None):
        self.redis_url = redis_url
        self.websocket_server = websocket_server
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="MonitoringService")
        
        # Redis connections
        self.redis_client = None
        self.pubsub = None
        
        # Services
        self.event_bus = get_event_bus()
        self.metrics_service = get_metrics_service()
        
        # Monitoring data
        self.event_metrics = EventMetrics()
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.system_health = SystemHealth()
        self.integration_status = IntegrationStatus()
        
        # Event tracking
        self.event_counts = defaultdict(int)
        self.event_times = deque(maxlen=1000)  # Track last 1000 events for rate calculation
        self.recent_events = deque(maxlen=100)  # Keep last 100 events for dashboard
        self.agent_heartbeats: Dict[str, datetime] = {}
        
        # Configuration
        self.heartbeat_timeout_yellow = 15  # seconds
        self.heartbeat_timeout_red = 30  # seconds
        self.metrics_update_interval = 5  # seconds
        self.cleanup_interval = 300  # 5 minutes
        
        # Threading
        self._lock = threading.RLock()
        self._monitoring_thread = None
        self._cleanup_thread = None
        
        self._setup_redis_connection()
    
    def _setup_redis_connection(self):
        """Setup Redis connection for event subscription."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"MonitoringService connected to Redis at {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis for monitoring: {e}")
            raise
    
    def start(self):
        """Start the monitoring service."""
        if self.running:
            logger.warning("MonitoringService is already running")
            return
        
        self.running = True
        
        try:
            # Subscribe to all events via Redis
            self._subscribe_to_events()
            
            # Start monitoring thread
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MonitoringServiceLoop"
            )
            self._monitoring_thread.start()
            
            # Start cleanup thread
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="MonitoringServiceCleanup"
            )
            self._cleanup_thread.start()
            
            logger.info("MonitoringService started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start MonitoringService: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the monitoring service."""
        if not self.running:
            return
        
        self.running = False
        
        # Unsubscribe from Redis
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        
        # Wait for threads to finish
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("MonitoringService stopped")
    
    def _subscribe_to_events(self):
        """Subscribe to all events via Redis pubsub."""
        try:
            # Subscribe to the main event channel
            self.pubsub.subscribe("software_factory:events")
            
            # Subscribe to agent heartbeat channel
            self.pubsub.subscribe("software_factory:agent_heartbeats")
            
            logger.info("MonitoringService subscribed to event channels")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")
            raise
    
    def _monitoring_loop(self):
        """Main monitoring loop that processes events and updates metrics."""
        logger.info("MonitoringService monitoring loop started")
        
        while self.running:
            try:
                # Process Redis messages
                message = self.pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    self.executor.submit(self._process_redis_message, message)
                
                # Update metrics periodically
                if int(time.time()) % self.metrics_update_interval == 0:
                    self.executor.submit(self._update_metrics)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
        
        logger.info("MonitoringService monitoring loop stopped")
    
    def _cleanup_loop(self):
        """Cleanup loop for old data and maintenance tasks."""
        logger.info("MonitoringService cleanup loop started")
        
        while self.running:
            try:
                time.sleep(self.cleanup_interval)
                
                if self.running:
                    self.executor.submit(self._cleanup_old_data)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
        
        logger.info("MonitoringService cleanup loop stopped")
    
    def _process_redis_message(self, message: Dict[str, Any]):
        """Process a message received from Redis."""
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            
            if channel == "software_factory:events":
                self._process_event_message(data)
            elif channel == "software_factory:agent_heartbeats":
                self._process_heartbeat_message(data)
            
        except Exception as e:
            logger.error(f"Error processing Redis message: {e}")
    
    def _process_event_message(self, event_data: Dict[str, Any]):
        """Process an event message and update metrics."""
        try:
            with self._lock:
                # Update event counts
                event_type = event_data.get('event_type', 'unknown')
                source = event_data.get('source', 'unknown')
                self.event_counts[event_type] += 1
                self.event_metrics.total_events += 1
                
                # Update Prometheus metrics for events
                self.metrics_service.increment_event_published(event_type, source)
                
                # Track event timing
                current_time = datetime.utcnow()
                self.event_times.append(current_time)
                
                # Store recent event
                recent_event = {
                    'event_type': event_type,
                    'event_id': event_data.get('event_id'),
                    'timestamp': current_time.isoformat(),
                    'source': event_data.get('source', 'unknown'),
                    'project_id': event_data.get('project_id'),
                    'actor': event_data.get('user_id'),
                    'payload_size': len(json.dumps(event_data.get('data', {})))
                }
                self.recent_events.append(recent_event)
                
                # Update agent metrics if event is from an agent
                source_agent = event_data.get('source')
                if source_agent and source_agent.endswith('_agent'):
                    self._update_agent_metrics_from_event(source_agent, event_data)
                
                # Stream to WebSocket if available
                if self.websocket_server:
                    self._stream_event_to_websocket(recent_event)
            
        except Exception as e:
            logger.error(f"Error processing event message: {e}")
    
    def _process_heartbeat_message(self, heartbeat_data: Dict[str, Any]):
        """Process an agent heartbeat message."""
        try:
            agent_id = heartbeat_data.get('agent_id')
            if not agent_id:
                return
            
            with self._lock:
                # Update heartbeat timestamp
                self.agent_heartbeats[agent_id] = datetime.utcnow()
                
                # Update or create agent metrics
                if agent_id not in self.agent_metrics:
                    self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
                
                agent_metrics = self.agent_metrics[agent_id]
                agent_metrics.last_activity = datetime.utcnow()
                agent_metrics.status = heartbeat_data.get('status', 'running')
                agent_metrics.current_load = heartbeat_data.get('current_load', 0)
                
                # Update heartbeat status based on timing
                agent_metrics.heartbeat_status = self._calculate_heartbeat_status(agent_id)
                
                # Update Prometheus metrics
                self.metrics_service.set_agent_status(agent_id, agent_metrics.status)
                self.metrics_service.set_agent_active_tasks(agent_id, agent_metrics.current_load)
            
        except Exception as e:
            logger.error(f"Error processing heartbeat message: {e}")
    
    def _update_agent_metrics_from_event(self, agent_id: str, event_data: Dict[str, Any]):
        """Update agent metrics based on processed event."""
        try:
            with self._lock:
                if agent_id not in self.agent_metrics:
                    self.agent_metrics[agent_id] = AgentMetrics(agent_id=agent_id)
                
                agent_metrics = self.agent_metrics[agent_id]
                agent_metrics.events_processed += 1
                agent_metrics.last_activity = datetime.utcnow()
                
                # Update Prometheus metrics for agent events
                event_type = event_data.get('event_type', 'unknown')
                status = event_data.get('metadata', {}).get('status', 'success')
                self.metrics_service.increment_agent_event(agent_id, event_type, status)
                
                # Update processing time if available
                processing_time = event_data.get('metadata', {}).get('processing_time')
                if processing_time:
                    # Update Prometheus processing time metric
                    self.metrics_service.record_agent_processing_time(agent_id, event_type, processing_time)
                    
                    # Simple moving average
                    if agent_metrics.average_processing_time == 0:
                        agent_metrics.average_processing_time = processing_time
                    else:
                        agent_metrics.average_processing_time = (
                            agent_metrics.average_processing_time * 0.9 + processing_time * 0.1
                        )
                
                # Update success rate
                status = event_data.get('metadata', {}).get('status', 'success')
                if status == 'success':
                    # Simple success rate calculation (could be improved with sliding window)
                    total_events = agent_metrics.events_processed
                    current_successes = agent_metrics.success_rate * (total_events - 1) + 1
                    agent_metrics.success_rate = current_successes / total_events
                else:
                    total_events = agent_metrics.events_processed
                    current_successes = agent_metrics.success_rate * (total_events - 1)
                    agent_metrics.success_rate = current_successes / total_events
            
        except Exception as e:
            logger.error(f"Error updating agent metrics: {e}")
    
    def _calculate_heartbeat_status(self, agent_id: str) -> str:
        """Calculate heartbeat status based on last heartbeat time."""
        if agent_id not in self.agent_heartbeats:
            return "red"
        
        last_heartbeat = self.agent_heartbeats[agent_id]
        time_since_heartbeat = (datetime.utcnow() - last_heartbeat).total_seconds()
        
        if time_since_heartbeat <= self.heartbeat_timeout_yellow:
            return "green"
        elif time_since_heartbeat <= self.heartbeat_timeout_red:
            return "yellow"
        else:
            return "red"
    
    def _update_metrics(self):
        """Update aggregated metrics."""
        try:
            with self._lock:
                # Calculate events per minute
                current_time = datetime.utcnow()
                one_minute_ago = current_time - timedelta(minutes=1)
                
                recent_event_count = sum(
                    1 for event_time in self.event_times 
                    if event_time >= one_minute_ago
                )
                self.event_metrics.events_per_minute = recent_event_count
                
                # Update events by type
                self.event_metrics.events_by_type = dict(self.event_counts)
                
                # Update recent events list
                self.event_metrics.recent_events = list(self.recent_events)
                
                # Update agent heartbeat statuses
                for agent_id in self.agent_metrics:
                    self.agent_metrics[agent_id].heartbeat_status = self._calculate_heartbeat_status(agent_id)
                
                # Update system health
                self._update_system_health()
                
                # Store metrics in database for historical analysis
                self._store_metrics_to_database()
                
                # Stream metrics to WebSocket
                if self.websocket_server:
                    self._stream_metrics_to_websocket()
            
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def _update_system_health(self):
        """Update system health metrics."""
        try:
            # Database health
            db_healthy = self._check_database_health()
            
            # Redis health
            redis_healthy = self._check_redis_health()
            
            # WebSocket health
            websocket_healthy = self._check_websocket_health()
            
            # Calculate overall score
            component_scores = []
            
            self.system_health.components = {
                'database': {
                    'status': 'healthy' if db_healthy else 'unhealthy',
                    'score': 100 if db_healthy else 0,
                    'last_check': datetime.utcnow().isoformat()
                },
                'redis': {
                    'status': 'healthy' if redis_healthy else 'unhealthy',
                    'score': 100 if redis_healthy else 0,
                    'last_check': datetime.utcnow().isoformat()
                },
                'websocket': {
                    'status': 'healthy' if websocket_healthy else 'unhealthy',
                    'score': 100 if websocket_healthy else 0,
                    'last_check': datetime.utcnow().isoformat()
                }
            }
            
            # Calculate overall score
            total_score = sum(comp['score'] for comp in self.system_health.components.values())
            self.system_health.overall_score = total_score / len(self.system_health.components)
            
            # Update Prometheus system metrics
            # Note: These would be more accurate with real system monitoring
            self.metrics_service.set_database_connections(5)  # Placeholder - would need real connection count
            self.metrics_service.set_redis_connections(2)     # Placeholder - would need real connection count
            
            # Update resource metrics (simplified)
            self.system_health.resources = {
                'cpu_usage': 0.0,  # Would need psutil for real CPU monitoring
                'memory_usage': 0.0,  # Would need psutil for real memory monitoring
                'disk_usage': 0.0,  # Would need psutil for real disk monitoring
                'network_latency': 0.0
            }
            
            # Update performance metrics
            self.system_health.performance = {
                'response_time': 0.0,  # Would calculate from request metrics
                'throughput': self.event_metrics.events_per_minute,
                'error_rate': self.event_metrics.error_rate
            }
            
        except Exception as e:
            logger.error(f"Error updating system health: {e}")
    
    def _check_database_health(self) -> bool:
        """Check database health."""
        try:
            # Simple database ping using SQLAlchemy text()
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def _check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def _check_websocket_health(self) -> bool:
        """Check WebSocket server health."""
        try:
            if self.websocket_server:
                # Check if WebSocket server is running and has connections
                return True  # Simplified check
            return False
        except Exception as e:
            logger.error(f"WebSocket health check failed: {e}")
            return False
    
    def _stream_event_to_websocket(self, event_data: Dict[str, Any]):
        """Stream event data to WebSocket clients."""
        try:
            if self.websocket_server:
                # Emit to monitor.events topic
                self.websocket_server.socketio.emit('monitor.events', event_data)
        except Exception as e:
            logger.error(f"Error streaming event to WebSocket: {e}")
    
    def _store_metrics_to_database(self):
        """Store current metrics to database for historical analysis."""
        try:
            current_time = datetime.utcnow()
            
            # Store event metrics
            MonitoringMetrics.record_metric(
                metric_type='event',
                metric_name='events_per_minute',
                value=self.event_metrics.events_per_minute,
                timestamp=current_time
            )
            
            MonitoringMetrics.record_metric(
                metric_type='event',
                metric_name='total_events',
                value=self.event_metrics.total_events,
                timestamp=current_time
            )
            
            # Store agent metrics
            for agent_id, agent in self.agent_metrics.items():
                # Update agent status in database
                AgentStatus.update_agent_status(
                    agent_id=agent_id,
                    status=agent.status,
                    heartbeat_status=agent.heartbeat_status,
                    events_processed=agent.events_processed,
                    success_rate=agent.success_rate,
                    average_processing_time=agent.average_processing_time,
                    current_load=agent.current_load,
                    last_activity=agent.last_activity,
                    last_heartbeat=self.agent_heartbeats.get(agent_id)
                )
                
                # Store agent metrics
                MonitoringMetrics.record_metric(
                    metric_type='agent',
                    metric_name='success_rate',
                    value=agent.success_rate,
                    source_id=agent_id,
                    timestamp=current_time
                )
                
                MonitoringMetrics.record_metric(
                    metric_type='agent',
                    metric_name='processing_time',
                    value=agent.average_processing_time,
                    source_id=agent_id,
                    timestamp=current_time
                )
            
            # Store system health
            SystemHealthModel.record_health(
                overall_score=self.system_health.overall_score,
                components=self.system_health.components,
                resources=self.system_health.resources,
                performance=self.system_health.performance,
                timestamp=current_time
            )
            
            # Store system metrics
            MonitoringMetrics.record_metric(
                metric_type='system',
                metric_name='health_score',
                value=self.system_health.overall_score,
                timestamp=current_time
            )
            
            # Commit all changes
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error storing metrics to database: {e}")
            db.session.rollback()
    
    def _stream_metrics_to_websocket(self):
        """Stream metrics data to WebSocket clients."""
        try:
            if self.websocket_server:
                metrics_data = {
                    'event_metrics': asdict(self.event_metrics),
                    'agent_metrics': {
                        agent_id: agent.to_dict() 
                        for agent_id, agent in self.agent_metrics.items()
                    },
                    'system_health': asdict(self.system_health),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Emit to monitor.metrics topic
                self.websocket_server.socketio.emit('monitor.metrics', metrics_data)
        except Exception as e:
            logger.error(f"Error streaming metrics to WebSocket: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        try:
            with self._lock:
                # Clean up old event times (keep last hour)
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                while self.event_times and self.event_times[0] < one_hour_ago:
                    self.event_times.popleft()
                
                # Clean up old agent heartbeats
                for agent_id in list(self.agent_heartbeats.keys()):
                    if (datetime.utcnow() - self.agent_heartbeats[agent_id]).total_seconds() > 3600:
                        del self.agent_heartbeats[agent_id]
            
            logger.debug("MonitoringService cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Public API methods
    
    def collect_event_metrics(self) -> EventMetrics:
        """Get current event metrics."""
        with self._lock:
            return EventMetrics(
                total_events=self.event_metrics.total_events,
                events_per_minute=self.event_metrics.events_per_minute,
                events_by_type=self.event_metrics.events_by_type.copy(),
                average_processing_time=self.event_metrics.average_processing_time,
                error_rate=self.event_metrics.error_rate,
                recent_events=list(self.event_metrics.recent_events)
            )
    
    def collect_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get current agent metrics."""
        with self._lock:
            return {
                agent_id: AgentMetrics(
                    agent_id=agent.agent_id,
                    status=agent.status,
                    events_processed=agent.events_processed,
                    success_rate=agent.success_rate,
                    average_processing_time=agent.average_processing_time,
                    current_load=agent.current_load,
                    last_activity=agent.last_activity,
                    heartbeat_status=agent.heartbeat_status
                )
                for agent_id, agent in self.agent_metrics.items()
            }
    
    def collect_system_health(self) -> SystemHealth:
        """Get current system health."""
        with self._lock:
            return SystemHealth(
                overall_score=self.system_health.overall_score,
                components=self.system_health.components.copy(),
                resources=self.system_health.resources.copy(),
                performance=self.system_health.performance.copy()
            )
    
    def collect_integration_status(self) -> IntegrationStatus:
        """Get current integration status."""
        with self._lock:
            # This would be expanded to check actual integrations
            return IntegrationStatus(
                integrations={
                    'slack': {
                        'status': 'healthy',
                        'last_check': datetime.utcnow().isoformat(),
                        'response_time': 0.1
                    },
                    'github': {
                        'status': 'healthy',
                        'last_check': datetime.utcnow().isoformat(),
                        'response_time': 0.2
                    }
                }
            )
    
    def process_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process alerts based on current metrics."""
        alerts = []
        
        try:
            # Check event rate alerts
            if self.event_metrics.events_per_minute > 100:  # Example threshold
                alerts.append({
                    'type': 'warning',
                    'title': 'High Event Rate',
                    'description': f'Event rate is {self.event_metrics.events_per_minute:.1f} events/minute',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'monitoring_service'
                })
            
            # Check agent health alerts
            for agent_id, agent in self.agent_metrics.items():
                if agent.heartbeat_status == 'red':
                    alerts.append({
                        'type': 'critical',
                        'title': f'Agent {agent_id} Unresponsive',
                        'description': f'Agent {agent_id} has not sent heartbeat for over {self.heartbeat_timeout_red} seconds',
                        'timestamp': datetime.utcnow().isoformat(),
                        'source': 'monitoring_service'
                    })
                elif agent.success_rate < 0.8:  # Less than 80% success rate
                    alerts.append({
                        'type': 'warning',
                        'title': f'Agent {agent_id} Low Success Rate',
                        'description': f'Agent {agent_id} success rate is {agent.success_rate:.1%}',
                        'timestamp': datetime.utcnow().isoformat(),
                        'source': 'monitoring_service'
                    })
            
            # Check system health alerts
            if self.system_health.overall_score < 80:
                alerts.append({
                    'type': 'warning',
                    'title': 'System Health Degraded',
                    'description': f'Overall system health score is {self.system_health.overall_score:.1f}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'monitoring_service'
                })
            
        except Exception as e:
            logger.error(f"Error processing alerts: {e}")
        
        return alerts
    
    def stream_to_websocket(self, data: Dict[str, Any]) -> None:
        """Stream data to WebSocket clients."""
        try:
            if self.websocket_server:
                self.websocket_server.socketio.emit('monitor.data', data)
        except Exception as e:
            logger.error(f"Error streaming to WebSocket: {e}")
    
    def get_historical_metrics(
        self,
        metric_type: str,
        metric_name: str,
        source_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical metrics from database."""
        try:
            from_time = datetime.utcnow() - timedelta(hours=hours)
            
            metrics = MonitoringMetrics.get_metrics(
                metric_type=metric_type,
                metric_name=metric_name,
                source_id=source_id,
                from_time=from_time,
                limit=1000
            )
            
            return [metric.to_dict() for metric in metrics]
            
        except Exception as e:
            logger.error(f"Error getting historical metrics: {e}")
            return []
    
    def get_agent_history(self, agent_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get agent performance history."""
        try:
            # Get agent status
            agent_status = AgentStatus.query.filter_by(agent_id=agent_id).first()
            
            # Get historical metrics
            success_rate_history = self.get_historical_metrics(
                'agent', 'success_rate', agent_id, hours
            )
            
            processing_time_history = self.get_historical_metrics(
                'agent', 'processing_time', agent_id, hours
            )
            
            return {
                'agent_status': agent_status.to_dict() if agent_status else None,
                'success_rate_history': success_rate_history,
                'processing_time_history': processing_time_history
            }
            
        except Exception as e:
            logger.error(f"Error getting agent history: {e}")
            return {}
    
    def get_system_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get system health history."""
        try:
            health_records = SystemHealthModel.get_health_history(hours)
            return [record.to_dict() for record in health_records]
            
        except Exception as e:
            logger.error(f"Error getting system health history: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring service statistics."""
        with self._lock:
            return {
                'running': self.running,
                'total_events_processed': self.event_metrics.total_events,
                'events_per_minute': self.event_metrics.events_per_minute,
                'active_agents': len(self.agent_metrics),
                'system_health_score': self.system_health.overall_score,
                'redis_connected': self._check_redis_health(),
                'database_connected': self._check_database_health(),
                'websocket_connected': self._check_websocket_health()
            }


# Global monitoring service instance
_monitoring_service_instance = None


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service_instance
    if _monitoring_service_instance is None:
        _monitoring_service_instance = MonitoringService()
    return _monitoring_service_instance


def init_monitoring_service(redis_url: str = "redis://localhost:6379/0", websocket_server: Optional[WebSocketServer] = None) -> MonitoringService:
    """Initialize the global monitoring service."""
    global _monitoring_service_instance
    _monitoring_service_instance = MonitoringService(redis_url=redis_url, websocket_server=websocket_server)
    return _monitoring_service_instance


def start_monitoring_service() -> None:
    """Start the global monitoring service."""
    monitoring_service = get_monitoring_service()
    if not monitoring_service.running:
        monitoring_service.start()
        logger.info("MonitoringService started")


def stop_monitoring_service() -> None:
    """Stop the global monitoring service."""
    monitoring_service = get_monitoring_service()
    monitoring_service.stop()
    logger.info("MonitoringService stopped")
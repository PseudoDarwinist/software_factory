"""
Prometheus metrics service for agent monitoring and system observability.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Optional prometheus_client import
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry, REGISTRY
    from prometheus_client.core import CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Mock prometheus classes if not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def inc(self, amount=1):
            pass
    
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def observe(self, amount):
            pass
    
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
        def set(self, value):
            pass
    
    class CollectorRegistry:
        pass
    
    REGISTRY = None
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MetricsService:
    """Prometheus metrics collection service for agents and system monitoring."""
    
    def __init__(self, port: int = 9100, registry: Optional[CollectorRegistry] = None):
        self.port = port
        self.registry = registry or REGISTRY
        self.server_thread = None
        self.running = False
        self._lock = threading.RLock()
        
        # Agent metrics
        self.agent_events_total = Counter(
            'agent_events_total',
            'Total number of events processed by agents',
            ['agent_id', 'event_type', 'status'],
            registry=self.registry
        )
        
        self.agent_processing_duration = Histogram(
            'agent_processing_duration_seconds',
            'Time spent processing events by agents',
            ['agent_id', 'event_type'],
            registry=self.registry
        )
        
        self.agent_active_tasks = Gauge(
            'agent_active_tasks',
            'Number of active tasks per agent',
            ['agent_id'],
            registry=self.registry
        )
        
        self.agent_status = Gauge(
            'agent_status',
            'Agent status (1=running, 0=stopped, -1=error)',
            ['agent_id'],
            registry=self.registry
        )
        
        # Event system metrics
        self.events_published_total = Counter(
            'events_published_total',
            'Total number of events published',
            ['event_type', 'source'],
            registry=self.registry
        )
        
        self.events_processed_total = Counter(
            'events_processed_total',
            'Total number of events processed',
            ['event_type', 'status'],
            registry=self.registry
        )
        
        self.event_processing_duration = Histogram(
            'event_processing_duration_seconds',
            'Time spent processing events',
            ['event_type'],
            registry=self.registry
        )
        
        # System metrics
        self.system_uptime = Gauge(
            'system_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        self.database_connections = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.redis_connections = Gauge(
            'redis_connections_active',
            'Number of active Redis connections',
            registry=self.registry
        )
        
        # AI service metrics
        self.ai_requests_total = Counter(
            'ai_requests_total',
            'Total number of AI service requests',
            ['model', 'status'],
            registry=self.registry
        )
        
        self.ai_request_duration = Histogram(
            'ai_request_duration_seconds',
            'Time spent on AI requests',
            ['model'],
            registry=self.registry
        )
        
        self.ai_tokens_used = Counter(
            'ai_tokens_used_total',
            'Total number of AI tokens used',
            ['model', 'type'],  # type: input/output
            registry=self.registry
        )
        
        # Track start time for uptime calculation
        self.start_time = datetime.utcnow()
    
    def start_server(self) -> None:
        """Start the Prometheus metrics HTTP server."""
        with self._lock:
            if self.running:
                logger.warning(f"Metrics server already running on port {self.port}")
                return
            
            if not PROMETHEUS_AVAILABLE:
                logger.warning("Prometheus client not available, metrics server will not start")
                return
            
            try:
                # Start HTTP server in a separate thread
                self.server_thread = threading.Thread(
                    target=self._run_server,
                    daemon=True,
                    name="PrometheusMetricsServer"
                )
                self.server_thread.start()
                
                self.running = True
                logger.info(f"Prometheus metrics server started on port {self.port}")
                
            except Exception as e:
                logger.error(f"Failed to start metrics server: {e}")
                raise
    
    def stop_server(self) -> None:
        """Stop the Prometheus metrics server."""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            logger.info("Prometheus metrics server stopped")
    
    def _run_server(self) -> None:
        """Run the Prometheus HTTP server."""
        if not PROMETHEUS_AVAILABLE:
            return
            
        try:
            start_http_server(self.port, registry=self.registry)
            
            # Update uptime metric periodically
            while self.running:
                uptime = (datetime.utcnow() - self.start_time).total_seconds()
                self.system_uptime.set(uptime)
                time.sleep(10)  # Update every 10 seconds
                
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
            self.running = False
    
    # Agent metrics methods
    def increment_agent_event(self, agent_id: str, event_type: str, status: str) -> None:
        """Increment agent event counter."""
        self.agent_events_total.labels(
            agent_id=agent_id,
            event_type=event_type,
            status=status
        ).inc()
    
    def record_agent_processing_time(self, agent_id: str, event_type: str, duration: float) -> None:
        """Record agent processing time."""
        self.agent_processing_duration.labels(
            agent_id=agent_id,
            event_type=event_type
        ).observe(duration)
    
    def set_agent_active_tasks(self, agent_id: str, count: int) -> None:
        """Set number of active tasks for an agent."""
        self.agent_active_tasks.labels(agent_id=agent_id).set(count)
    
    def set_agent_status(self, agent_id: str, status: str) -> None:
        """Set agent status (running=1, stopped=0, error=-1)."""
        status_value = {
            'running': 1,
            'stopped': 0,
            'error': -1,
            'paused': 0.5
        }.get(status, 0)
        
        self.agent_status.labels(agent_id=agent_id).set(status_value)
    
    # Event system metrics methods
    def increment_event_published(self, event_type: str, source: str = "system") -> None:
        """Increment published events counter."""
        self.events_published_total.labels(
            event_type=event_type,
            source=source
        ).inc()
    
    def increment_event_processed(self, event_type: str, status: str) -> None:
        """Increment processed events counter."""
        self.events_processed_total.labels(
            event_type=event_type,
            status=status
        ).inc()
    
    def record_event_processing_time(self, event_type: str, duration: float) -> None:
        """Record event processing time."""
        self.event_processing_duration.labels(event_type=event_type).observe(duration)
    
    # System metrics methods
    def set_database_connections(self, count: int) -> None:
        """Set number of active database connections."""
        self.database_connections.set(count)
    
    def set_redis_connections(self, count: int) -> None:
        """Set number of active Redis connections."""
        self.redis_connections.set(count)
    
    # AI service metrics methods
    def increment_ai_request(self, model: str, status: str) -> None:
        """Increment AI request counter."""
        self.ai_requests_total.labels(model=model, status=status).inc()
    
    def record_ai_request_time(self, model: str, duration: float) -> None:
        """Record AI request processing time."""
        self.ai_request_duration.labels(model=model).observe(duration)
    
    def increment_ai_tokens(self, model: str, token_type: str, count: int) -> None:
        """Increment AI token usage counter."""
        self.ai_tokens_used.labels(model=model, type=token_type).inc(count)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            'prometheus_available': PROMETHEUS_AVAILABLE,
            'server_running': self.running,
            'server_port': self.port,
            'uptime_seconds': uptime,
            'metrics_available': [
                'agent_events_total',
                'agent_processing_duration_seconds',
                'agent_active_tasks',
                'agent_status',
                'events_published_total',
                'events_processed_total',
                'event_processing_duration_seconds',
                'system_uptime_seconds',
                'database_connections_active',
                'redis_connections_active',
                'ai_requests_total',
                'ai_request_duration_seconds',
                'ai_tokens_used_total'
            ]
        }


# Global metrics service instance
_metrics_service_instance = None


def get_metrics_service() -> MetricsService:
    """Get the global metrics service instance."""
    global _metrics_service_instance
    if _metrics_service_instance is None:
        _metrics_service_instance = MetricsService()
    return _metrics_service_instance


def init_metrics_service(port: int = 9100) -> MetricsService:
    """Initialize the global metrics service."""
    global _metrics_service_instance
    _metrics_service_instance = MetricsService(port=port)
    return _metrics_service_instance


def start_metrics_server(port: int = 9100) -> None:
    """Start the Prometheus metrics server."""
    metrics_service = get_metrics_service()
    if not metrics_service.running:
        metrics_service.port = port
        metrics_service.start_server()
        logger.info(f"Prometheus metrics server started on port {port}")


def ensure_metrics_server_running(port: int = 9100) -> None:
    """Ensure the Prometheus metrics server is running."""
    metrics_service = get_metrics_service()
    if not metrics_service.running:
        start_metrics_server(port)


def stop_metrics_server() -> None:
    """Stop the Prometheus metrics server."""
    metrics_service = get_metrics_service()
    metrics_service.stop_server()
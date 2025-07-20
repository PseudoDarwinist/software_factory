#!/usr/bin/env python3
"""
Event Bus Service - Redis-based Event Publishing and Subscribing
Handles event distribution across Software Factory components
"""

import redis
import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional, List
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from contextlib import contextmanager

try:
    from ..core.events import Event, EventType, validate_event_schema
    from ..services.distributed_cache import get_cache_invalidation_service
except ImportError:
    from core.events import Event, EventType, validate_event_schema
    from services.distributed_cache import get_cache_invalidation_service


logger = logging.getLogger(__name__)


@dataclass
class EventSubscription:
    """Event subscription configuration"""
    event_type: str
    callback: Callable[[Event], None]
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None


class EventBus:
    """Redis-based event bus for Software Factory"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", max_workers: int = 4):
        self.redis_url = redis_url
        self.max_workers = max_workers
        self.redis_client = None
        self.pubsub = None
        self.subscriptions: Dict[str, List[EventSubscription]] = {}
        self.running = False
        self.subscriber_thread = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.event_stats = {
            'published': 0,
            'received': 0,
            'processed': 0,
            'errors': 0
        }
        
        # Event channel configuration
        self.event_channel = "software_factory:events"
        self.system_channel = "software_factory:system"
        
        self._setup_redis_connection()
    
    def _setup_redis_connection(self):
        """Setup Redis connection and pubsub"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def start(self):
        """Start the event bus subscriber"""
        if self.running:
            logger.warning("Event bus is already running")
            return
        
        self.running = True
        
        # Subscribe to event channels
        self.pubsub.subscribe(self.event_channel)
        self.pubsub.subscribe(self.system_channel)
        
        # Start subscriber thread
        self.subscriber_thread = threading.Thread(
            target=self._subscriber_loop,
            daemon=True,
            name="EventBusSubscriber"
        )
        self.subscriber_thread.start()
        
        logger.info("Event bus started successfully")
    
    def stop(self):
        """Stop the event bus"""
        if not self.running:
            return
        
        self.running = False
        
        # Unsubscribe from channels
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        
        # Wait for subscriber thread to finish
        if self.subscriber_thread and self.subscriber_thread.is_alive():
            self.subscriber_thread.join(timeout=5)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Event bus stopped")
    
    def publish(self, event: Event) -> bool:
        """Publish an event to the event bus"""
        try:
            # Validate event
            if not validate_event_schema(event):
                logger.error(f"Invalid event schema: {event.event_type}")
                self.event_stats['errors'] += 1
                return False
            
            # Serialize event
            event_data = event.to_json()
            
            # Publish to Redis
            result = self.redis_client.publish(self.event_channel, event_data)
            
            if result > 0:
                self.event_stats['published'] += 1
                logger.debug(f"Published event: {event.event_type} ({event.event_id})")
                
                # Trigger cache invalidation for relevant events
                try:
                    cache_invalidation_service = get_cache_invalidation_service()
                    if cache_invalidation_service:
                        invalidated = cache_invalidation_service.invalidate_for_event(
                            event.event_type, 
                            event.data
                        )
                        if invalidated > 0:
                            logger.debug(f"Cache invalidation: {invalidated} entries for {event.event_type}")
                except Exception as e:
                    logger.error(f"Cache invalidation failed for event {event.event_type}: {e}")
                
                return True
            else:
                logger.warning(f"No subscribers for event: {event.event_type}")
                return True  # Not an error, just no subscribers
                
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            self.event_stats['errors'] += 1
            return False
    
    def subscribe(self, event_type: str, callback: Callable[[Event], None], 
                  correlation_id: Optional[str] = None, user_id: Optional[str] = None,
                  project_id: Optional[str] = None) -> str:
        """Subscribe to events of a specific type"""
        
        subscription = EventSubscription(
            event_type=event_type,
            callback=callback,
            correlation_id=correlation_id,
            user_id=user_id,
            project_id=project_id
        )
        
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        
        self.subscriptions[event_type].append(subscription)
        
        subscription_id = f"{event_type}:{len(self.subscriptions[event_type])}"
        logger.info(f"Added subscription: {subscription_id}")
        
        return subscription_id
    
    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]):
        """Unsubscribe from events"""
        if event_type in self.subscriptions:
            self.subscriptions[event_type] = [
                sub for sub in self.subscriptions[event_type] 
                if sub.callback != callback
            ]
            
            if not self.subscriptions[event_type]:
                del self.subscriptions[event_type]
            
            logger.info(f"Removed subscription for: {event_type}")
    
    def _subscriber_loop(self):
        """Main subscriber loop"""
        logger.info("Event bus subscriber started")
        
        while self.running:
            try:
                # Get message with timeout
                message = self.pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    self.event_stats['received'] += 1
                    
                    # Process message in thread pool
                    self.executor.submit(self._process_message, message)
                
            except Exception as e:
                logger.error(f"Error in subscriber loop: {e}")
                self.event_stats['errors'] += 1
                time.sleep(1)  # Brief pause before retrying
        
        logger.info("Event bus subscriber stopped")
    
    def _process_message(self, message: Dict[str, Any]):
        """Process a received message"""
        try:
            # Parse event
            event_data = json.loads(message['data'])
            event = Event.from_dict(event_data)
            
            # Find matching subscriptions
            matching_subscriptions = []
            
            if event.event_type in self.subscriptions:
                for subscription in self.subscriptions[event.event_type]:
                    if self._matches_subscription(event, subscription):
                        matching_subscriptions.append(subscription)
            
            # Execute callbacks
            for subscription in matching_subscriptions:
                try:
                    subscription.callback(event)
                    self.event_stats['processed'] += 1
                except Exception as e:
                    logger.error(f"Error in event callback for {event.event_type}: {e}")
                    self.event_stats['errors'] += 1
            
            if not matching_subscriptions:
                logger.debug(f"No subscribers for event: {event.event_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.event_stats['errors'] += 1
    
    def _matches_subscription(self, event: Event, subscription: EventSubscription) -> bool:
        """Check if event matches subscription criteria"""
        # Check correlation ID if specified
        if subscription.correlation_id and event.correlation_id != subscription.correlation_id:
            return False
        
        # Check user ID if specified
        if subscription.user_id and event.user_id != subscription.user_id:
            return False
        
        # Check project ID if specified
        if subscription.project_id and event.project_id != subscription.project_id:
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'running': self.running,
            'subscriptions': {
                event_type: len(subs) for event_type, subs in self.subscriptions.items()
            },
            'stats': self.event_stats.copy(),
            'redis_url': self.redis_url
        }
    
    def health_check(self) -> bool:
        """Check if event bus is healthy"""
        try:
            self.redis_client.ping()
            return self.running
        except Exception:
            return False
    
    @contextmanager
    def event_context(self, correlation_id: str, user_id: Optional[str] = None, 
                     project_id: Optional[str] = None):
        """Context manager for event correlation"""
        # This could be used to automatically add correlation info to events
        # For now, it's a placeholder for future enhancement
        yield


# Global event bus instance
_event_bus_instance = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance


def init_event_bus(redis_url: str = "redis://localhost:6379/0", max_workers: int = 4) -> EventBus:
    """Initialize the global event bus"""
    global _event_bus_instance
    _event_bus_instance = EventBus(redis_url, max_workers)
    return _event_bus_instance


# Convenience functions for common operations
def publish_event(event: Event) -> bool:
    """Publish an event using the global event bus"""
    return get_event_bus().publish(event)


def subscribe_to_event(event_type: str, callback: Callable[[Event], None], 
                      correlation_id: Optional[str] = None, user_id: Optional[str] = None,
                      project_id: Optional[str] = None) -> str:
    """Subscribe to events using the global event bus"""
    return get_event_bus().subscribe(event_type, callback, correlation_id, user_id, project_id)


def unsubscribe_from_event(event_type: str, callback: Callable[[Event], None]):
    """Unsubscribe from events using the global event bus"""
    return get_event_bus().unsubscribe(event_type, callback)
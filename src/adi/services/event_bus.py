"""
ADI Event Bus

Redis-based event bus for ADI Engine components.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import redis

logger = logging.getLogger(__name__)


class ADIEventBus:
    """Redis-based event bus for ADI Engine."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.subscribers = {}
        
    def publish(self, event_type: str, data: Dict[str, Any], project_id: Optional[str] = None):
        """
        Publish an event to the event bus.
        
        Args:
            event_type: Type of event (e.g., 'decision_log_ingested', 'insight_generated')
            data: Event payload
            project_id: Optional project ID for scoped events
        """
        try:
            event = {
                'type': event_type,
                'data': data,
                'project_id': project_id,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'adi_engine'
            }
            
            # Publish to general ADI channel
            channel = 'adi:events'
            self.redis.publish(channel, json.dumps(event))
            
            # Publish to project-specific channel if project_id provided
            if project_id:
                project_channel = f'adi:events:{project_id}'
                self.redis.publish(project_channel, json.dumps(event))
            
            logger.debug(f"Published event {event_type} to {channel}")
            
        except Exception as e:
            logger.error(f"Error publishing event {event_type}: {str(e)}")
    
    def subscribe(self, event_type: str, handler: Callable, project_id: Optional[str] = None):
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to handle the event
            project_id: Optional project ID for scoped subscription
        """
        try:
            channel = 'adi:events'
            if project_id:
                channel = f'adi:events:{project_id}'
            
            if channel not in self.subscribers:
                self.subscribers[channel] = {}
            
            if event_type not in self.subscribers[channel]:
                self.subscribers[channel][event_type] = []
            
            self.subscribers[channel][event_type].append(handler)
            
            logger.info(f"Subscribed to {event_type} events on {channel}")
            
        except Exception as e:
            logger.error(f"Error subscribing to {event_type}: {str(e)}")
    
    def start_listening(self):
        """Start listening for events (blocking operation)."""
        try:
            pubsub = self.redis.pubsub()
            
            # Subscribe to all channels we have handlers for
            for channel in self.subscribers.keys():
                pubsub.subscribe(channel)
            
            logger.info(f"Started listening on channels: {list(self.subscribers.keys())}")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    self._handle_message(message)
                    
        except Exception as e:
            logger.error(f"Error in event listener: {str(e)}")
    
    def _handle_message(self, message):
        """Handle incoming event message."""
        try:
            channel = message['channel'].decode('utf-8')
            event_data = json.loads(message['data'].decode('utf-8'))
            event_type = event_data.get('type')
            
            if channel in self.subscribers and event_type in self.subscribers[channel]:
                for handler in self.subscribers[channel][event_type]:
                    try:
                        handler(event_data)
                    except Exception as e:
                        logger.error(f"Error in event handler for {event_type}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")


class ADICache:
    """Redis-based caching for ADI Engine."""
    
    def __init__(self, redis_client: redis.Redis, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = 'adi:cache:'
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            cache_key = f"{self.key_prefix}{key}"
            data = self.redis.get(cache_key)
            
            if data:
                return json.loads(data.decode('utf-8'))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        try:
            cache_key = f"{self.key_prefix}{key}"
            ttl = ttl or self.default_ttl
            
            serialized = json.dumps(value, default=str)
            return self.redis.setex(cache_key, ttl, serialized)
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        try:
            cache_key = f"{self.key_prefix}{key}"
            return bool(self.redis.delete(cache_key))
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False
    
    def get_domain_pack(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get cached domain pack for a project."""
        return self.get(f"domain_pack:{project_id}")
    
    def set_domain_pack(self, project_id: str, pack_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache domain pack for a project (30 minute TTL by default)."""
        return self.set(f"domain_pack:{project_id}", pack_data, ttl)
    
    def invalidate_domain_pack(self, project_id: str) -> bool:
        """Invalidate cached domain pack for a project."""
        return self.delete(f"domain_pack:{project_id}")
    
    def get_insights_summary(self, project_id: str, window_hours: int) -> Optional[Dict[str, Any]]:
        """Get cached insights summary."""
        return self.get(f"insights_summary:{project_id}:{window_hours}")
    
    def set_insights_summary(self, project_id: str, window_hours: int, summary: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache insights summary (5 minute TTL by default)."""
        return self.set(f"insights_summary:{project_id}:{window_hours}", summary, ttl)


# Event type constants
class ADIEvents:
    """Constants for ADI event types."""
    
    DECISION_LOG_INGESTED = 'decision_log_ingested'
    INSIGHT_GENERATED = 'insight_generated'
    INSIGHT_UPDATED = 'insight_updated'
    KNOWLEDGE_ADDED = 'knowledge_added'
    KNOWLEDGE_UPDATED = 'knowledge_updated'
    DOMAIN_PACK_UPDATED = 'domain_pack_updated'
    EVAL_COMPLETED = 'eval_completed'
    SCORING_COMPLETED = 'scoring_completed'
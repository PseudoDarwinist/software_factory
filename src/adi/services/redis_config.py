"""
Redis Configuration for ADI Engine

Centralized Redis client configuration and initialization.
"""

import os
import redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration and client management."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._event_bus = None
        self._cache = None
    
    def get_client(self) -> redis.Redis:
        """Get Redis client instance (singleton)."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> redis.Redis:
        """Create Redis client from environment configuration."""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            
            # Parse Redis URL and create client
            client = redis.from_url(
                redis_url,
                decode_responses=False,  # Keep as bytes for pubsub
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            client.ping()
            logger.info(f"Connected to Redis at {redis_url}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    def get_event_bus(self):
        """Get ADI event bus instance."""
        if self._event_bus is None:
            from .event_bus import ADIEventBus
            self._event_bus = ADIEventBus(self.get_client())
        return self._event_bus
    
    def get_cache(self):
        """Get ADI cache instance."""
        if self._cache is None:
            from .event_bus import ADICache
            self._cache = ADICache(self.get_client())
        return self._cache
    
    def health_check(self) -> dict:
        """Check Redis connection health."""
        try:
            client = self.get_client()
            
            # Test basic operations
            test_key = 'adi:health_check'
            client.set(test_key, 'ok', ex=10)
            value = client.get(test_key)
            client.delete(test_key)
            
            if value == b'ok':
                return {
                    'status': 'healthy',
                    'redis_connected': True,
                    'operations_working': True
                }
            else:
                return {
                    'status': 'unhealthy',
                    'redis_connected': True,
                    'operations_working': False,
                    'error': 'Redis operations not working correctly'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'redis_connected': False,
                'operations_working': False,
                'error': str(e)
            }


# Global Redis configuration instance
redis_config = RedisConfig()
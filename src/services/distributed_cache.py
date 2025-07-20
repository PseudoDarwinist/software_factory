"""
Distributed caching service with Redis backend for multi-user support
Provides TTL-based caching with event-driven invalidation and session management
"""

import time
import threading
import json
import pickle
import redis
from typing import Any, Optional, Dict, Callable, Union, List
from datetime import datetime, timedelta
import logging
from flask import session, request, g
import hashlib
import uuid

logger = logging.getLogger(__name__)

# Redis connection pool
_redis_pool = None

def get_redis_connection(redis_url: str = 'redis://localhost:6379/0') -> redis.Redis:
    """Get Redis connection with connection pooling"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(redis_url, decode_responses=False)
    return redis.Redis(connection_pool=_redis_pool)


class DistributedCache:
    """
    Redis-based distributed cache with session management and event-driven invalidation
    Supports multi-user concurrent access with proper isolation
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0', 
                 default_ttl: int = 300, key_prefix: str = 'sf_cache'):
        self.redis_client = get_redis_connection(redis_url)
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._local_cache = {}  # L1 cache for ultra-fast access
        self._local_cache_lock = threading.RLock()
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    def _make_key(self, key: str, namespace: str = None, user_id: str = None) -> str:
        """Create namespaced cache key with optional user isolation"""
        parts = [self.key_prefix]
        
        if namespace:
            parts.append(namespace)
        
        if user_id:
            parts.append(f"user:{user_id}")
        
        parts.append(key)
        return ":".join(parts)
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        try:
            # Try JSON first for simple types
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    def get(self, key: str, namespace: str = None, user_id: str = None) -> Optional[Any]:
        """Get value from cache with L1/L2 cache hierarchy"""
        cache_key = self._make_key(key, namespace, user_id)
        
        # Check L1 cache first
        with self._local_cache_lock:
            if cache_key in self._local_cache:
                entry = self._local_cache[cache_key]
                if entry['expires_at'] > time.time():
                    return entry['value']
                else:
                    del self._local_cache[cache_key]
        
        # Check Redis (L2 cache)
        try:
            data = self.redis_client.get(cache_key)
            if data:
                value = self._deserialize_value(data)
                
                # Store in L1 cache for faster access
                with self._local_cache_lock:
                    self._local_cache[cache_key] = {
                        'value': value,
                        'expires_at': time.time() + 30  # L1 cache for 30 seconds
                    }
                
                return value
        except Exception as e:
            logger.error(f"Redis get error for key {cache_key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            namespace: str = None, user_id: str = None) -> bool:
        """Set value in cache with TTL"""
        cache_key = self._make_key(key, namespace, user_id)
        ttl = ttl or self.default_ttl
        
        try:
            # Store in Redis
            serialized_value = self._serialize_value(value)
            self.redis_client.setex(cache_key, ttl, serialized_value)
            
            # Store in L1 cache
            with self._local_cache_lock:
                self._local_cache[cache_key] = {
                    'value': value,
                    'expires_at': time.time() + min(ttl, 30)  # L1 cache for max 30 seconds
                }
            
            return True
        except Exception as e:
            logger.error(f"Redis set error for key {cache_key}: {e}")
            return False
    
    def delete(self, key: str, namespace: str = None, user_id: str = None) -> bool:
        """Delete specific cache entry"""
        cache_key = self._make_key(key, namespace, user_id)
        
        try:
            # Remove from Redis
            deleted = self.redis_client.delete(cache_key)
            
            # Remove from L1 cache
            with self._local_cache_lock:
                self._local_cache.pop(cache_key, None)
            
            return deleted > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {cache_key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str, namespace: str = None) -> int:
        """Invalidate all keys matching a pattern"""
        search_pattern = self._make_key(pattern, namespace)
        
        try:
            keys = self.redis_client.keys(search_pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                
                # Clear matching keys from L1 cache
                with self._local_cache_lock:
                    to_remove = [k for k in self._local_cache.keys() 
                               if any(k.decode() == key.decode() for key in keys)]
                    for k in to_remove:
                        del self._local_cache[k]
                
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis pattern invalidation error for {search_pattern}: {e}")
            return 0
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[int] = None,
                   namespace: str = None, user_id: str = None) -> Any:
        """Get value from cache or compute and cache it"""
        value = self.get(key, namespace, user_id)
        if value is not None:
            return value
        
        # Compute new value
        try:
            value = factory()
            self.set(key, value, ttl, namespace, user_id)
            return value
        except Exception as e:
            logger.error(f"Factory function error for key {key}: {e}")
            raise
    
    def increment(self, key: str, amount: int = 1, namespace: str = None, 
                  user_id: str = None, ttl: Optional[int] = None) -> int:
        """Atomic increment operation"""
        cache_key = self._make_key(key, namespace, user_id)
        
        try:
            value = self.redis_client.incr(cache_key, amount)
            if ttl:
                self.redis_client.expire(cache_key, ttl)
            return value
        except Exception as e:
            logger.error(f"Redis increment error for key {cache_key}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = self.redis_client.info()
            
            # Count our keys
            our_keys = self.redis_client.keys(f"{self.key_prefix}:*")
            
            with self._local_cache_lock:
                l1_entries = len(self._local_cache)
                l1_expired = sum(1 for entry in self._local_cache.values() 
                               if entry['expires_at'] <= time.time())
            
            return {
                'redis_connected': True,
                'redis_memory_usage': info.get('used_memory_human', 'unknown'),
                'redis_total_keys': info.get('keyspace_db0', {}).get('keys', 0),
                'our_cache_keys': len(our_keys),
                'l1_cache_entries': l1_entries,
                'l1_cache_expired': l1_expired,
                'l1_cache_active': l1_entries - l1_expired
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'redis_connected': False, 'error': str(e)}
    
    def clear_namespace(self, namespace: str = None, user_id: str = None) -> int:
        """Clear all entries in a namespace"""
        pattern = self._make_key("*", namespace, user_id)
        return self.invalidate_pattern(pattern)
    
    def cleanup_l1_cache(self):
        """Remove expired entries from L1 cache"""
        current_time = time.time()
        
        with self._local_cache_lock:
            expired_keys = [
                key for key, entry in self._local_cache.items()
                if entry['expires_at'] <= current_time
            ]
            
            for key in expired_keys:
                del self._local_cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired L1 cache entries")
            
            return len(expired_keys)


class SessionManager:
    """
    Redis-based session management for multi-user concurrent access
    Provides secure session handling with automatic cleanup
    """
    
    def __init__(self, cache: DistributedCache, session_ttl: int = 3600):
        self.cache = cache
        self.session_ttl = session_ttl
        self.session_namespace = "sessions"
    
    def create_session(self, user_data: Dict[str, Any] = None) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'user_data': user_data or {},
            'ip_address': getattr(request, 'remote_addr', None) if request else None,
            'user_agent': getattr(request, 'user_agent', None) if request else None
        }
        
        self.cache.set(
            key=session_id,
            value=session_data,
            ttl=self.session_ttl,
            namespace=self.session_namespace
        )
        
        logger.info(f"Created session {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data and update last accessed time"""
        if not session_id:
            return None
        
        session_data = self.cache.get(session_id, namespace=self.session_namespace)
        
        if session_data:
            # Update last accessed time
            session_data['last_accessed'] = time.time()
            self.cache.set(
                key=session_id,
                value=session_data,
                ttl=self.session_ttl,
                namespace=self.session_namespace
            )
            
            return session_data
        
        return None
    
    def update_session(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """Update session data"""
        session_data = self.get_session(session_id)
        
        if session_data:
            session_data['user_data'].update(user_data)
            session_data['last_accessed'] = time.time()
            
            return self.cache.set(
                key=session_id,
                value=session_data,
                ttl=self.session_ttl,
                namespace=self.session_namespace
            )
        
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if self.cache.delete(session_id, namespace=self.session_namespace):
            logger.info(f"Deleted session {session_id}")
            return True
        return False
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions (admin function)"""
        try:
            pattern = self.cache._make_key("*", namespace=self.session_namespace)
            keys = self.cache.redis_client.keys(pattern)
            
            sessions = []
            for key in keys:
                session_data = self.cache.redis_client.get(key)
                if session_data:
                    sessions.append(self.cache._deserialize_value(session_data))
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (called by cleanup job)"""
        # Redis handles TTL automatically, but we can get stats
        active_sessions = self.get_active_sessions()
        logger.info(f"Session cleanup: {len(active_sessions)} active sessions")
        return len(active_sessions)


class CacheInvalidationService:
    """
    Event-driven cache invalidation service
    Listens to domain events and invalidates related cache entries
    """
    
    def __init__(self, cache: DistributedCache):
        self.cache = cache
        self.invalidation_rules = {
            'project.created': ['projects:*', 'project_count', 'user_projects:*'],
            'project.updated': ['projects:*', 'project:{project_id}:*'],
            'project.deleted': ['projects:*', 'project:{project_id}:*', 'project_count'],
            'conversation.created': ['conversations:*', 'project:{project_id}:conversations'],
            'conversation.updated': ['conversation:{conversation_id}:*'],
            'stage.updated': ['stages:*', 'project:{project_id}:stages'],
            'system_map.generated': ['project:{project_id}:system_map', 'project:{project_id}:status'],
            'ai.response': ['ai_context:*'],  # Clear AI context cache after responses
        }
    
    def invalidate_for_event(self, event_type: str, event_data: Dict[str, Any]) -> int:
        """Invalidate cache entries based on domain event"""
        if event_type not in self.invalidation_rules:
            return 0
        
        patterns = self.invalidation_rules[event_type]
        total_invalidated = 0
        
        for pattern in patterns:
            # Replace placeholders with actual values from event data
            formatted_pattern = pattern.format(**event_data)
            
            try:
                invalidated = self.cache.invalidate_pattern(formatted_pattern)
                total_invalidated += invalidated
                logger.debug(f"Invalidated {invalidated} entries for pattern {formatted_pattern}")
            except Exception as e:
                logger.error(f"Error invalidating pattern {formatted_pattern}: {e}")
        
        if total_invalidated > 0:
            logger.info(f"Event {event_type}: invalidated {total_invalidated} cache entries")
        
        return total_invalidated
    
    def add_invalidation_rule(self, event_type: str, patterns: List[str]):
        """Add custom invalidation rule"""
        if event_type in self.invalidation_rules:
            self.invalidation_rules[event_type].extend(patterns)
        else:
            self.invalidation_rules[event_type] = patterns
        
        logger.info(f"Added invalidation rule for {event_type}: {patterns}")


class CacheWarmingService:
    """
    Cache warming service for predictive data loading
    Pre-loads frequently accessed data to improve performance
    """
    
    def __init__(self, cache: DistributedCache):
        self.cache = cache
        self.warming_jobs = {}
    
    def register_warming_job(self, name: str, factory: Callable[[], Any], 
                           key: str, ttl: int = 300, interval: int = 240):
        """Register a cache warming job"""
        self.warming_jobs[name] = {
            'factory': factory,
            'key': key,
            'ttl': ttl,
            'interval': interval,
            'last_run': 0
        }
        logger.info(f"Registered cache warming job: {name}")
    
    def run_warming_cycle(self):
        """Run all warming jobs that are due"""
        current_time = time.time()
        
        for name, job in self.warming_jobs.items():
            if current_time - job['last_run'] >= job['interval']:
                try:
                    logger.debug(f"Running cache warming job: {name}")
                    value = job['factory']()
                    self.cache.set(job['key'], value, job['ttl'])
                    job['last_run'] = current_time
                    logger.debug(f"Cache warming job {name} completed")
                except Exception as e:
                    logger.error(f"Cache warming job {name} failed: {e}")
    
    def warm_project_data(self, project_id: str):
        """Warm cache for specific project data"""
        try:
            # This would be implemented with actual data fetching
            logger.info(f"Warming cache for project {project_id}")
            # Example: Pre-load project details, conversations, stages, etc.
        except Exception as e:
            logger.error(f"Error warming cache for project {project_id}: {e}")


# Global instances
distributed_cache = None
session_manager = None
cache_invalidation_service = None
cache_warming_service = None


def init_distributed_cache(redis_url: str = 'redis://localhost:6379/0', 
                          default_ttl: int = 300) -> DistributedCache:
    """Initialize distributed cache system"""
    global distributed_cache, session_manager, cache_invalidation_service, cache_warming_service
    
    distributed_cache = DistributedCache(redis_url=redis_url, default_ttl=default_ttl)
    session_manager = SessionManager(distributed_cache, session_ttl=3600)
    cache_invalidation_service = CacheInvalidationService(distributed_cache)
    cache_warming_service = CacheWarmingService(distributed_cache)
    
    # Register common warming jobs
    cache_warming_service.register_warming_job(
        name='project_count',
        factory=lambda: {'count': 0},  # Would fetch actual count
        key='project_count',
        ttl=300,
        interval=240
    )
    
    logger.info("Distributed cache system initialized")
    return distributed_cache


def get_distributed_cache() -> DistributedCache:
    """Get the global distributed cache instance"""
    global distributed_cache
    if distributed_cache is None:
        distributed_cache = init_distributed_cache()
    return distributed_cache


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    global session_manager
    if session_manager is None:
        init_distributed_cache()
    return session_manager


def get_cache_invalidation_service() -> CacheInvalidationService:
    """Get the cache invalidation service"""
    global cache_invalidation_service
    if cache_invalidation_service is None:
        init_distributed_cache()
    return cache_invalidation_service


def get_cache_warming_service() -> CacheWarmingService:
    """Get the cache warming service"""
    global cache_warming_service
    if cache_warming_service is None:
        init_distributed_cache()
    return cache_warming_service
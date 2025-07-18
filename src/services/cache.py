"""
Simple in-memory caching service for status polling system
Provides TTL-based caching for frequently requested data
"""

import time
import threading
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Individual cache entry with TTL support"""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.created_at > self.ttl_seconds
    
    def get_value(self) -> Any:
        """Get cached value and update access statistics"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class StatusCache:
    """
    Simple in-memory cache for status polling system
    Thread-safe with TTL support and automatic cleanup
    """
    
    def __init__(self, default_ttl: int = 30, cleanup_interval: int = 60):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._shutdown = False
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            entry = self.cache.get(key)
            if entry and not entry.is_expired():
                return entry.get_value()
            elif entry:
                # Remove expired entry
                del self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL override"""
        ttl = ttl or self.default_ttl
        with self._lock:
            self.cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete specific cache entry"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """Get value from cache or compute and cache it"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Compute new value
        value = factory()
        self.set(key, value, ttl)
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_entries = len(self.cache)
            expired_entries = sum(1 for entry in self.cache.values() if entry.is_expired())
            total_accesses = sum(entry.access_count for entry in self.cache.values())
            
            return {
                'total_entries': total_entries,
                'active_entries': total_entries - expired_entries,
                'expired_entries': expired_entries,
                'total_accesses': total_accesses,
                'hit_rate': self._calculate_hit_rate(),
                'memory_usage_estimate': self._estimate_memory_usage()
            }
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder - would need request tracking)"""
        # This is a simplified calculation
        # In a real implementation, we'd track cache hits vs misses
        return 0.0
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes (rough approximation)"""
        # Very rough estimate - in production, use memory_profiler or similar
        return len(self.cache) * 1024  # Assume ~1KB per entry
    
    def _cleanup_expired_entries(self) -> int:
        """Remove expired entries and return count removed"""
        with self._lock:
            expired_keys = [
                key for key, entry in self.cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def _start_cleanup_thread(self):
        """Start background thread for periodic cleanup"""
        def cleanup_worker():
            while not self._shutdown:
                try:
                    time.sleep(self.cleanup_interval)
                    if not self._shutdown:
                        self._cleanup_expired_entries()
                except Exception as e:
                    logger.error(f"Cache cleanup thread error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info(f"Started cache cleanup thread (interval: {self.cleanup_interval}s)")
    
    def shutdown(self):
        """Shutdown cache and cleanup thread"""
        self._shutdown = True
        self.clear()
        logger.info("Status cache shutdown complete")


# Global cache instance
status_cache = None


def get_status_cache() -> StatusCache:
    """Get the global status cache instance"""
    global status_cache
    if status_cache is None:
        status_cache = StatusCache(default_ttl=30, cleanup_interval=60)
    return status_cache


def init_status_cache(default_ttl: int = 30, cleanup_interval: int = 60) -> StatusCache:
    """Initialize the global status cache"""
    global status_cache
    status_cache = StatusCache(default_ttl=default_ttl, cleanup_interval=cleanup_interval)
    return status_cache
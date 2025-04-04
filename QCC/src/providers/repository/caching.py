"""
Caching system for Quantum Cellular Computing repository.

This module provides functionality for caching frequently accessed repository
data, reducing latency and database load for common operations.
"""

import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """
    Represents a cached item.
    
    Attributes:
        key: Cache key
        value: Cached value
        expiry: Expiry timestamp
        last_accessed: Last access timestamp
    """
    key: str
    value: Any
    expiry: float  # Timestamp when entry expires
    last_accessed: float = 0.0  # Timestamp of last access
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > self.expiry
    
    def touch(self) -> None:
        """Update last access timestamp."""
        self.last_accessed = time.time()


class CachingManager:
    """
    Manages caches for the repository.
    
    This class provides functionality for caching frequently accessed data,
    with support for time-based expiration, automatic cleanup, and cache
    statistics.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize the caching manager.
        
        Args:
            max_size: Maximum number of entries in the cache
            default_ttl: Default time-to-live for cache entries in seconds
        """
        self.caches = {}  # cache_name -> {key -> CacheEntry}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {}  # cache_name -> {hits, misses, expirations}
        self.cleanup_interval = 60  # Seconds between cleanup runs
        
        # Start background cleanup task
        self._background_task = None
    
    async def start_background_cleanup(self):
        """Start the background cache cleanup task."""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._background_cleanup())
    
    async def stop_background_cleanup(self):
        """Stop the background cache cleanup task."""
        if self._background_task is not None:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
    
    async def _background_cleanup(self):
        """Periodically clean up expired cache entries."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                self.cleanup_expired()
        except asyncio.CancelledError:
            # Final cleanup before shutting down
            self.cleanup_expired()
            raise
        except Exception as e:
            logger.error(f"Error in background cache cleanup: {e}")
    
    def get(self, cache_name: str, key: str) -> Tuple[Any, bool]:
        """
        Get a value from the cache.
        
        Args:
            cache_name: Name of the cache
            key: Cache key
            
        Returns:
            Tuple of (value, found) where found is True if the key was found
        """
        # Initialize cache and stats if needed
        if cache_name not in self.caches:
            self.caches[cache_name] = {}
            self.stats[cache_name] = {"hits": 0, "misses": 0, "expirations": 0}
        
        # Check if key exists in cache
        cache = self.caches[cache_name]
        
        if key in cache:
            entry = cache[key]
            
            # Check if expired
            if entry.is_expired():
                # Remove expired entry
                del cache[key]
                self.stats[cache_name]["expirations"] += 1
                self.stats[cache_name]["misses"] += 1
                return None, False
            
            # Update access time
            entry.touch()
            self.stats[cache_name]["hits"] += 1
            return entry.value, True
        
        # Key not found
        self.stats[cache_name]["misses"] += 1
        return None, False
    
    def set(self, cache_name: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            cache_name: Name of the cache
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for default)
        """
        # Initialize cache if needed
        if cache_name not in self.caches:
            self.caches[cache_name] = {}
            self.stats[cache_name] = {"hits": 0, "misses": 0, "expirations": 0}
        
        # Check if cache is full
        cache = self.caches[cache_name]
        if len(cache) >= self.max_size and key not in cache:
            # Evict least recently used entry
            self._evict_lru(cache_name)
        
        # Calculate expiry
        ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + ttl
        
        # Create or update entry
        cache[key] = CacheEntry(
            key=key,
            value=value,
            expiry=expiry,
            last_accessed=time.time()
        )
    
    def invalidate(self, cache_name: str, key: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            cache_name: Name of the cache
            key: Specific key to invalidate (None for all keys)
            
        Returns:
            Number of entries invalidated
        """
        if cache_name not in self.caches:
            return 0
        
        cache = self.caches[cache_name]
        
        if key is not None:
            # Invalidate specific key
            if key in cache:
                del cache[key]
                return 1
            return 0
        
        # Invalidate all keys
        count = len(cache)
        self.caches[cache_name] = {}
        return count
    
    def cleanup_expired(self) -> Dict[str, int]:
        """
        Remove all expired entries from all caches.
        
        Returns:
            Dictionary with count of removed entries per cache
        """
        removed_counts = {}
        
        for cache_name, cache in self.caches.items():
            # Find expired keys
            expired_keys = []
            for key, entry in cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                    self.stats[cache_name]["expirations"] += 1
            
            # Remove expired entries
            for key in expired_keys:
                del cache[key]
            
            removed_counts[cache_name] = len(expired_keys)
            
        return removed_counts
    
    def get_stats(self, cache_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Args:
            cache_name: Specific cache to get stats for (None for all)
            
        Returns:
            Dictionary with cache statistics
        """
        if cache_name is not None:
            if cache_name not in self.stats:
                return {
                    "name": cache_name,
                    "exists": False
                }
            
            cache = self.caches[cache_name]
            stats = self.stats[cache_name]
            
            return {
                "name": cache_name,
                "exists": True,
                "size": len(cache),
                "max_size": self.max_size,
                "hits": stats["hits"],
                "misses": stats["misses"],
                "expirations": stats["expirations"],
                "hit_ratio": stats["hits"] / (stats["hits"] + stats["misses"]) if (stats["hits"] + stats["misses"]) > 0 else 0
            }
        
        # Get stats for all caches
        all_stats = {}
        total_size = 0
        total_hits = 0
        total_misses = 0
        total_expirations = 0
        
        for name, cache in self.caches.items():
            stats = self.stats[name]
            
            cache_stats = {
                "size": len(cache),
                "hits": stats["hits"],
                "misses": stats["misses"],
                "expirations": stats["expirations"],
                "hit_ratio": stats["hits"] / (stats["hits"] + stats["misses"]) if (stats["hits"] + stats["misses"]) > 0 else 0
            }
            
            all_stats[name] = cache_stats
            total_size += len(cache)
            total_hits += stats["hits"]
            total_misses += stats["misses"]
            total_expirations += stats["expirations"]
        
        return {
            "caches": all_stats,
            "total_size": total_size,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_expirations": total_expirations,
            "total_hit_ratio": total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0,
            "cache_count": len(self.caches)
        }
    
    def reset_stats(self, cache_name: Optional[str] = None) -> None:
        """
        Reset cache statistics.
        
        Args:
            cache_name: Specific cache to reset stats for (None for all)
        """
        if cache_name is not None:
            if cache_name in self.stats:
                self.stats[cache_name] = {"hits": 0, "misses": 0, "expirations": 0}
        else:
            for name in self.stats:
                self.stats[name] = {"hits": 0, "misses": 0, "expirations": 0}
    
    def _evict_lru(self, cache_name: str) -> bool:
        """
        Evict the least recently used cache entry.
        
        Args:
            cache_name: Name of the cache
            
        Returns:
            True if an entry was evicted, False otherwise
        """
        if cache_name not in self.caches:
            return False
        
        cache = self.caches[cache_name]
        
        if not cache:
            return False
        
        # Find least recently used entry
        lru_key = None
        lru_time = float('inf')
        
        for key, entry in cache.items():
            if entry.last_accessed < lru_time:
                lru_key = key
                lru_time = entry.last_accessed
        
        if lru_key:
            del cache[lru_key]
            return True
        
        return False


class AsyncCache:
    """
    Decorator class for caching async function results.
    
    This class provides a decorator for caching the results of async functions,
    with support for function-specific TTL and cache invalidation.
    """
    
    def __init__(self, cache_manager: CachingManager):
        """
        Initialize the async cache decorator.
        
        Args:
            cache_manager: Caching manager instance
        """
        self.cache_manager = cache_manager
    
    def __call__(self, cache_name: str, key_fn: Optional[Callable] = None, ttl: Optional[int] = None):
        """
        Create a caching decorator for an async function.
        
        Args:
            cache_name: Name of the cache
            key_fn: Function to generate cache key from arguments (None for default)
            ttl: Time-to-live in seconds (None for default)
            
        Returns:
            Decorator function
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_fn:
                    key = key_fn(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [str(arg) for arg in args]
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    key = f"{func.__name__}:{','.join(key_parts)}"
                
                # Try to get from cache
                value, found = self.cache_manager.get(cache_name, key)
                if found:
                    return value
                
                # Call function
                result = await func(*args, **kwargs)
                
                # Store in cache
                self.cache_manager.set(cache_name, key, result, ttl)
                
                return result
            
            return wrapper
        
        return decorator

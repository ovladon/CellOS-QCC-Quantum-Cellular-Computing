"""
Caching system for cell distribution.

This module provides caching functionality for cell distribution
to improve performance and reduce load on the repository.
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)

class CellDeliveryCache:
    """
    Cache for frequently delivered cells.
    
    The CellDeliveryCache stores recently and frequently delivered
    cells to reduce repository load and improve delivery performance.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize the cell delivery cache.
        
        Args:
            max_size: Maximum number of cells to cache
            ttl_seconds: Time-to-live for cached cells in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Use OrderedDict for LRU behavior
        self.cache = OrderedDict()
        self.expiry_times = {}
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        logger.info(f"Cell delivery cache initialized with capacity {max_size}, TTL {ttl_seconds}s")
    
    def get(self, cell_id: str) -> Optional[Any]:
        """
        Get a cell from the cache.
        
        Args:
            cell_id: The ID of the cell
            
        Returns:
            The cached cell or None if not found or expired
        """
        with self.lock:
            # Check if cell is in cache
            if cell_id not in self.cache:
                self.stats["misses"] += 1
                return None
            
            # Check if cell has expired
            if time.time() > self.expiry_times.get(cell_id, 0):
                # Remove expired cell
                self.cache.pop(cell_id)
                self.expiry_times.pop(cell_id, None)
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
                return None
            
            # Move to end of OrderedDict to maintain LRU order
            cell = self.cache.pop(cell_id)
            self.cache[cell_id] = cell
            
            # Update expiry time to extend TTL
            self.expiry_times[cell_id] = time.time() + self.ttl_seconds
            
            self.stats["hits"] += 1
            return cell
    
    def add(self, cell_id: str, cell: Any) -> None:
        """
        Add a cell to the cache.
        
        Args:
            cell_id: The ID of the cell
            cell: The cell to cache
        """
        with self.lock:
            # Check if cache is full and we need to evict
            if len(self.cache) >= self.max_size and cell_id not in self.cache:
                # Evict least recently used item (first in OrderedDict)
                _, oldest_cell_id = next(iter(self.cache.items()))
                self.cache.popitem(last=False)
                self.expiry_times.pop(oldest_cell_id, None)
                self.stats["evictions"] += 1
            
            # Add or update cell
            self.cache[cell_id] = cell
            self.expiry_times[cell_id] = time.time() + self.ttl_seconds
    
    def remove(self, cell_id: str) -> bool:
        """
        Remove a cell from the cache.
        
        Args:
            cell_id: The ID of the cell
            
        Returns:
            True if the cell was found and removed, False otherwise
        """
        with self.lock:
            if cell_id in self.cache:
                self.cache.pop(cell_id)
                self.expiry_times.pop(cell_id, None)
                return True
            return False
    
    def clear(self) -> None:
        """
        Clear the entire cache.
        """
        with self.lock:
            self.cache.clear()
            self.expiry_times.clear()
    
    def get_size(self) -> int:
        """
        Get the current size of the cache.
        
        Returns:
            Number of items in the cache
        """
        with self.lock:
            return len(self.cache)
    
    def get_hit_count(self) -> int:
        """
        Get the number of cache hits.
        
        Returns:
            Number of cache hits
        """
        with self.lock:
            return self.stats["hits"]
    
    def get_miss_count(self) -> int:
        """
        Get the number of cache misses.
        
        Returns:
            Number of cache misses
        """
        with self.lock:
            return self.stats["misses"]
    
    def get_hit_rate(self) -> float:
        """
        Get the cache hit rate.
        
        Returns:
            Cache hit rate as a percentage
        """
        with self.lock:
            total = self.stats["hits"] + self.stats["misses"]
            if total == 0:
                return 0.0
            return self.stats["hits"] / total * 100

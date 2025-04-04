"""
Rate limiter for QCC Provider Services.

This module provides functionality for rate limiting cell delivery
requests to prevent abuse and ensure fair resource allocation.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Implements rate limiting for cell delivery requests.
    
    The RateLimiter tracks request rates for different assemblers
    and rejects requests that exceed configured limits.
    """
    
    def __init__(
        self,
        max_requests_per_second: int = 5,
        max_requests_per_minute: int = 60,
        max_requests_per_hour: int = 1000,
        trusted_assemblers: List[str] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests_per_second: Maximum requests per second per assembler
            max_requests_per_minute: Maximum requests per minute per assembler
            max_requests_per_hour: Maximum requests per hour per assembler
            trusted_assemblers: List of assembler IDs exempt from rate limiting
        """
        self.max_requests_per_second = max_requests_per_second
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_hour = max_requests_per_hour
        self.trusted_assemblers = set(trusted_assemblers or [])
        
        # Request tracking
        self.second_counters = defaultdict(lambda: deque(maxlen=5))
        self.minute_counters = defaultdict(lambda: deque(maxlen=5))
        self.hour_counters = defaultdict(lambda: deque(maxlen=5))
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "limited_requests": 0,
            "limited_by_second": 0,
            "limited_by_minute": 0,
            "limited_by_hour": 0
        }
        
        logger.info(
            f"Rate limiter initialized with limits: "
            f"{max_requests_per_second}/sec, {max_requests_per_minute}/min, {max_requests_per_hour}/hour"
        )
    
    def allow_request(self, assembler_id: str) -> bool:
        """
        Check if a request is allowed based on rate limits.
        
        Args:
            assembler_id: The ID of the requesting assembler
            
        Returns:
            True if the request is allowed, False otherwise
        """
        self.stats["total_requests"] += 1
        
        # Trusted assemblers bypass rate limiting
        if assembler_id in self.trusted_assemblers:
            self.stats["allowed_requests"] += 1
            return True
        
        # Get current timestamp
        now = time.time()
        current_second = int(now)
        current_minute = current_second // 60
        current_hour = current_minute // 60
        
        # Clean up expired entries
        self._clean_expired_entries(assembler_id, now)
        
        # Check second limit
        second_requests = self._count_requests(self.second_counters[assembler_id], current_second - 1, current_second)
        if second_requests >= self.max_requests_per_second:
            self.stats["limited_requests"] += 1
            self.stats["limited_by_second"] += 1
            return False
        
        # Check minute limit
        minute_requests = self._count_requests(self.minute_counters[assembler_id], current_minute - 1, current_minute)
        if minute_requests >= self.max_requests_per_minute:
            self.stats["limited_requests"] += 1
            self.stats["limited_by_minute"] += 1
            return False
        
        # Check hour limit
        hour_requests = self._count_requests(self.hour_counters[assembler_id], current_hour - 1, current_hour)
        if hour_requests >= self.max_requests_per_hour:
            self.stats["limited_requests"] += 1
            self.stats["limited_by_hour"] += 1
            return False
        
        # Record this request
        self.second_counters[assembler_id].append((current_second, 1))
        self.minute_counters[assembler_id].append((current_minute, 1))
        self.hour_counters[assembler_id].append((current_hour, 1))
        
        self.stats["allowed_requests"] += 1
        return True
    
    def _count_requests(self, counter: deque, time_frame_start: int, time_frame_end: int) -> int:
        """
        Count requests within a time frame.
        
        Args:
            counter: Counter deque
            time_frame_start: Start of time frame
            time_frame_end: End of time frame
            
        Returns:
            Number of requests in the time frame
        """
        return sum(count for timestamp, count in counter if time_frame_start <= timestamp <= time_frame_end)
    
    def _clean_expired_entries(self, assembler_id: str, now: float) -> None:
        """
        Clean up expired entries from counters.
        
        Args:
            assembler_id: The assembler ID
            now: Current timestamp
        """
        current_second = int(now)
        current_minute = current_second // 60
        current_hour = current_minute // 60
        
        # Keep only entries from the last second
        self.second_counters[assembler_id] = deque(
            [(t, c) for t, c in self.second_counters[assembler_id] if t >= current_second - 1],
            maxlen=self.second_counters[assembler_id].maxlen
        )
        
        # Keep only entries from the last minute
        self.minute_counters[assembler_id] = deque(
            [(t, c) for t, c in self.minute_counters[assembler_id] if t >= current_minute - 1],
            maxlen=self.minute_counters[assembler_id].maxlen
        )
        
        # Keep only entries from the last hour
        self.hour_counters[assembler_id] = deque(
            [(t, c) for t, c in self.hour_counters[assembler_id] if t >= current_hour - 1],
            maxlen=self.hour_counters[assembler_id].maxlen
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.
        
        Returns:
            Rate limiter statistics
        """
        if self.stats["total_requests"] > 0:
            self.stats["limited_percentage"] = (
                self.stats["limited_requests"] / self.stats["total_requests"] * 100
            )
        else:
            self.stats["limited_percentage"] = 0
            
        return self.stats

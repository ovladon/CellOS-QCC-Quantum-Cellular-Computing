"""
Delivery tracking for QCC Provider Services.

This module provides functionality for tracking cell delivery requests
and their status throughout the delivery lifecycle.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum, auto
import json

logger = logging.getLogger(__name__)

class DeliveryStatus(Enum):
    """Enum for delivery status values."""
    QUEUED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class DeliveryTracker:
    """
    Tracks the status and history of cell delivery requests.
    
    The DeliveryTracker maintains information about ongoing and completed
    delivery requests, including their current status, history, and
    performance metrics.
    """
    
    def __init__(self, max_history_size: int = 10000):
        """
        Initialize the delivery tracker.
        
        Args:
            max_history_size: Maximum number of completed deliveries to keep in history
        """
        self.max_history_size = max_history_size
        self.active_deliveries = {}  # request_id -> delivery info
        self.completed_deliveries = {}  # request_id -> delivery info
        self.delivery_stats = {
            "total_requests": 0,
            "active_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "cancelled_count": 0,
            "avg_completion_time_ms": 0
        }
    
    def start_tracking(self, request_id: str, request: Any) -> None:
        """
        Start tracking a delivery request.
        
        Args:
            request_id: The ID of the request
            request: The delivery request
        """
        self.delivery_stats["total_requests"] += 1
        self.delivery_stats["active_count"] += 1
        
        # Create tracking entry
        self.active_deliveries[request_id] = {
            "request_id": request_id,
            "assembler_id": getattr(request, "assembler_id", None),
            "cell_id": getattr(request, "cell_id", None),
            "capability": getattr(request, "capability", None),
            "status": DeliveryStatus.QUEUED.name,
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "history": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "status": DeliveryStatus.QUEUED.name,
                    "message": "Request queued for processing"
                }
            ]
        }
    
    def update_status(
        self,
        request_id: str,
        status: DeliveryStatus,
        message: str,
        details: Dict[str, Any] = None
    ) -> None:
        """
        Update the status of a delivery request.
        
        Args:
            request_id: The ID of the request
            status: The new status
            message: Status message
            details: Additional details about the status
        """
        if request_id not in self.active_deliveries:
            logger.warning(f"Attempted to update status for unknown request: {request_id}")
            return
        
        # Update tracking info
        delivery_info = self.active_deliveries[request_id]
        delivery_info["status"] = status.name
        delivery_info["last_updated"] = datetime.now().isoformat()
        
        # Add history entry
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": status.name,
            "message": message
        }
        
        if details:
            history_entry["details"] = details
        
        delivery_info["history"].append(history_entry)
        
        # Handle completed or failed deliveries
        if status in [DeliveryStatus.COMPLETED, DeliveryStatus.FAILED, DeliveryStatus.CANCELLED]:
            # Calculate completion time
            start_time = datetime.fromisoformat(delivery_info["start_time"])
            end_time = datetime.now()
            delivery_info["completion_time"] = end_time.isoformat()
            delivery_info["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
            
            # Update statistics
            self.delivery_stats["active_count"] -= 1
            
            if status == DeliveryStatus.COMPLETED:
                self.delivery_stats["completed_count"] += 1
                
                # Update average completion time
                total_time = (
                    self.delivery_stats["avg_completion_time_ms"] * 
                    (self.delivery_stats["completed_count"] - 1) +
                    delivery_info["duration_ms"]
                )
                self.delivery_stats["avg_completion_time_ms"] = (
                    total_time / self.delivery_stats["completed_count"]
                    if self.delivery_stats["completed_count"] > 0 else 0
                )
                
            elif status == DeliveryStatus.FAILED:
                self.delivery_stats["failed_count"] += 1
                
            elif status == DeliveryStatus.CANCELLED:
                self.delivery_stats["cancelled_count"] += 1
            
            # Move to completed deliveries
            self.completed_deliveries[request_id] = delivery_info
            del self.active_deliveries[request_id]
            
            # Prune history if needed
            self._prune_history_if_needed()
    
    def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a delivery request.
        
        Args:
            request_id: The ID of the request
            
        Returns:
            Status information or None if not found
        """
        # Check active deliveries
        if request_id in self.active_deliveries:
            return self.active_deliveries[request_id]
        
        # Check completed deliveries
        if request_id in self.completed_deliveries:
            return self.completed_deliveries[request_id]
        
        return None
    
    def get_active_count(self) -> int:
        """
        Get the number of active delivery requests.
        
        Returns:
            Number of active requests
        """
        return self.delivery_stats["active_count"]
    
    def get_completed_count(self) -> int:
        """
        Get the number of completed delivery requests.
        
        Returns:
            Number of completed requests
        """
        return self.delivery_stats["completed_count"]
    
    def get_failed_count(self) -> int:
        """
        Get the number of failed delivery requests.
        
        Returns:
            Number of failed requests
        """
        return self.delivery_stats["failed_count"]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get overall delivery statistics.
        
        Returns:
            Delivery statistics
        """
        return self.delivery_stats
    
    def _prune_history_if_needed(self) -> None:
        """
        Prune the history of completed deliveries if it exceeds the maximum size.
        """
        if len(self.completed_deliveries) > self.max_history_size:
            # Sort by completion time (oldest first)
            sorted_keys = sorted(
                self.completed_deliveries.keys(),
                key=lambda k: self.completed_deliveries[k].get("completion_time", "")
            )
            
            # Remove oldest entries
            excess_count = len(self.completed_deliveries) - self.max_history_size
            for key in sorted_keys[:excess_count]:
                del self.completed_deliveries[key]

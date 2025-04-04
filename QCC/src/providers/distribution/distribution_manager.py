"""
Distribution Manager for QCC Provider Services

This module implements the core functionality for distributing cells from
providers to assemblers. It handles request queueing, prioritization,
delivery tracking, and load balancing.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import uuid

from qcc.providers.repository import RepositoryManager
from qcc.providers.verification import VerificationService
from qcc.common.exceptions import DistributionError, CellNotFoundError
from qcc.common.models import Cell, DeliveryRequest, DeliveryStatus
from .protocols import ProtocolHandler, HTTPProtocolHandler, WSProtocolHandler
from .tracking import DeliveryTracker
from .rate_limiter import RateLimiter
from .cache import CellDeliveryCache

logger = logging.getLogger(__name__)

class DistributionManager:
    """
    Main class responsible for distributing cells from providers to assemblers.
    
    The DistributionManager coordinates the process of delivering cells to
    assemblers based on requests. It handles:
    - Request prioritization and queueing
    - Protocol selection for delivery
    - Rate limiting and throttling
    - Delivery tracking and retry logic
    - Load balancing across provider instances
    - Caching of frequently requested cells
    """
    
    def __init__(
        self, 
        repository_manager: RepositoryManager,
        verification_service: VerificationService,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the DistributionManager.
        
        Args:
            repository_manager: Manager for accessing the cell repository
            verification_service: Service for verifying cells before distribution
            config: Configuration options for distribution
        """
        self.repository_manager = repository_manager
        self.verification_service = verification_service
        self.config = config or {}
        
        # Initialize subcomponents
        self.delivery_tracker = DeliveryTracker()
        self.rate_limiter = RateLimiter(
            max_requests_per_second=self.config.get("max_requests_per_second", 100),
            max_requests_per_minute=self.config.get("max_requests_per_minute", 5000),
            max_requests_per_hour=self.config.get("max_requests_per_hour", 100000)
        )
        
        # Initialize delivery cache if enabled
        cache_enabled = self.config.get("enable_cache", True)
        if cache_enabled:
            self.delivery_cache = CellDeliveryCache(
                max_size=self.config.get("cache_max_size", 1000),
                ttl_seconds=self.config.get("cache_ttl_seconds", 3600)
            )
        else:
            self.delivery_cache = None
        
        # Initialize protocol handlers
        self.protocol_handlers = {
            "http": HTTPProtocolHandler(self.config.get("http_config", {})),
            "websocket": WSProtocolHandler(self.config.get("websocket_config", {}))
        }
        
        # Custom protocol handlers
        custom_protocols = self.config.get("custom_protocols", {})
        for protocol_name, protocol_config in custom_protocols.items():
            if "class" in protocol_config:
                try:
                    handler_class = protocol_config.pop("class")
                    self.protocol_handlers[protocol_name] = handler_class(protocol_config)
                    logger.info(f"Registered custom protocol handler: {protocol_name}")
                except Exception as e:
                    logger.error(f"Failed to register custom protocol handler {protocol_name}: {e}")
        
        # Initialize request queue
        self.request_queue = asyncio.PriorityQueue()
        
        # Start background tasks
        self.queue_processor_task = None
        self.is_running = False
        
        logger.info("Distribution Manager initialized")
    
    async def start(self):
        """Start the distribution manager and background tasks."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start queue processor
        self.queue_processor_task = asyncio.create_task(self._process_queue())
        
        logger.info("Distribution Manager started")
    
    async def stop(self):
        """Stop the distribution manager and clean up resources."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel queue processor
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
            
        logger.info("Distribution Manager stopped")
    
    async def handle_delivery_request(self, request: DeliveryRequest) -> str:
        """
        Handle a request for cell delivery.
        
        Args:
            request: The delivery request
            
        Returns:
            Request ID for tracking
            
        Raises:
            DistributionError: If the request cannot be processed
        """
        # Validate request
        if not request.cell_id and not request.capability:
            raise DistributionError("Either cell_id or capability must be provided")
        
        if not request.assembler_id:
            raise DistributionError("Assembler ID is required")
        
        # Apply rate limiting
        if not self.rate_limiter.allow_request(request.assembler_id):
            raise DistributionError("Rate limit exceeded for this assembler")
        
        # Generate request ID if not provided
        request_id = request.request_id or str(uuid.uuid4())
        
        # Set request timestamp
        request.timestamp = datetime.now().isoformat()
        
        # Determine priority
        priority = request.priority if request.priority is not None else 5
        
        # Put request in queue
        await self.request_queue.put((priority, request_id, request))
        
        # Initialize tracking
        self.delivery_tracker.start_tracking(request_id, request)
        
        logger.info(f"Queued delivery request {request_id} for assembler {request.assembler_id}")
        
        return request_id
    
    async def get_delivery_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get the status of a cell delivery request.
        
        Args:
            request_id: The ID of the delivery request
            
        Returns:
            Status information for the request
        """
        return self.delivery_tracker.get_status(request_id)
    
    async def cancel_delivery(self, request_id: str) -> bool:
        """
        Cancel a pending cell delivery request.
        
        Args:
            request_id: The ID of the delivery request
            
        Returns:
            True if successfully cancelled, False otherwise
        """
        status = self.delivery_tracker.get_status(request_id)
        
        if not status:
            return False
        
        # Can only cancel requests that are queued or in progress
        if status["status"] not in [DeliveryStatus.QUEUED, DeliveryStatus.IN_PROGRESS]:
            return False
        
        # Update status to cancelled
        self.delivery_tracker.update_status(
            request_id,
            DeliveryStatus.CANCELLED,
            message="Delivery cancelled by request"
        )
        
        logger.info(f"Cancelled delivery request {request_id}")
        
        return True
    
    async def get_distribution_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the distribution system.
        
        Returns:
            Distribution statistics
        """
        stats = {
            "queue_size": self.request_queue.qsize(),
            "active_deliveries": self.delivery_tracker.get_active_count(),
            "completed_deliveries": self.delivery_tracker.get_completed_count(),
            "failed_deliveries": self.delivery_tracker.get_failed_count(),
            "rate_limiter": self.rate_limiter.get_stats(),
            "protocols": {}
        }
        
        # Get stats from each protocol handler
        for protocol_name, handler in self.protocol_handlers.items():
            stats["protocols"][protocol_name] = handler.get_stats()
        
        # Get cache stats if enabled
        if self.delivery_cache:
            stats["cache"] = {
                "size": self.delivery_cache.get_size(),
                "hit_count": self.delivery_cache.get_hit_count(),
                "miss_count": self.delivery_cache.get_miss_count(),
                "hit_rate": self.delivery_cache.get_hit_rate()
            }
        
        return stats
    
    async def _process_queue(self):
        """
        Background task to process the request queue.
        This runs continuously while the manager is active.
        """
        logger.info("Queue processor started")
        
        while self.is_running:
            try:
                # Get next request from queue
                priority, request_id, request = await self.request_queue.get()
                
                # Process the request
                self.delivery_tracker.update_status(
                    request_id,
                    DeliveryStatus.IN_PROGRESS,
                    message="Processing delivery request"
                )
                
                # Process in a separate task to avoid blocking the queue
                asyncio.create_task(
                    self._deliver_cell(request_id, request)
                )
                
                # Mark task as done
                self.request_queue.task_done()
                
            except asyncio.CancelledError:
                # Queue processor was cancelled
                break
                
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1)  # Avoid tight loop in case of errors
        
        logger.info("Queue processor stopped")
    
    async def _deliver_cell(self, request_id: str, request: DeliveryRequest):
        """
        Process a cell delivery request.
        
        Args:
            request_id: The ID of the request
            request: The delivery request
        """
        logger.debug(f"Processing delivery request {request_id}")
        
        try:
            # Check if cell is in cache if caching is enabled
            cell = None
            cached = False
            
            if self.delivery_cache and request.cell_id:
                cell = self.delivery_cache.get(request.cell_id)
                cached = cell is not None
                
                if cached:
                    logger.debug(f"Cache hit for cell {request.cell_id}")
            
            # If not in cache, retrieve from repository
            if not cell:
                if request.cell_id:
                    # Get specific cell by ID
                    cell = await self.repository_manager.get_cell(request.cell_id)
                elif request.capability:
                    # Find cell for capability
                    cell = await self.repository_manager.find_cell_for_capability(
                        request.capability,
                        version=request.version,
                        constraints=request.constraints
                    )
                
                if not cell:
                    raise CellNotFoundError("Cell not found in repository")
                
                # Verify cell before delivery
                await self.verification_service.verify_cell(
                    cell, 
                    request.quantum_signature
                )
                
                # Add to cache if caching is enabled
                if self.delivery_cache:
                    self.delivery_cache.add(cell.id, cell)
            
            # Determine protocol for delivery
            protocol = request.protocol or "http"
            
            if protocol not in self.protocol_handlers:
                raise DistributionError(f"Unsupported protocol: {protocol}")
            
            protocol_handler = self.protocol_handlers[protocol]
            
            # Update tracking information
            self.delivery_tracker.update_status(
                request_id,
                DeliveryStatus.IN_PROGRESS,
                message=f"Delivering cell using {protocol} protocol",
                details={
                    "cell_id": cell.id,
                    "protocol": protocol,
                    "cached": cached
                }
            )
            
            # Deliver the cell
            delivery_result = await protocol_handler.deliver_cell(
                cell=cell,
                assembler_id=request.assembler_id,
                quantum_signature=request.quantum_signature,
                options=request.options
            )
            
            # Update tracking with success
            self.delivery_tracker.update_status(
                request_id,
                DeliveryStatus.COMPLETED,
                message="Cell delivered successfully",
                details={
                    "cell_id": cell.id,
                    "protocol": protocol,
                    "delivery_time_ms": delivery_result.get("delivery_time_ms", 0),
                    "cached": cached
                }
            )
            
            logger.info(f"Successfully delivered cell {cell.id} to assembler {request.assembler_id}")
            
        except Exception as e:
            # Update tracking with failure
            self.delivery_tracker.update_status(
                request_id,
                DeliveryStatus.FAILED,
                message=f"Cell delivery failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
            
            logger.error(f"Failed to deliver cell for request {request_id}: {e}")

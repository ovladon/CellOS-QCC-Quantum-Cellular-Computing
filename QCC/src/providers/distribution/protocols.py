"""
Protocol handlers for cell distribution.

This module defines the protocol handlers used for cell delivery
from providers to assemblers, including HTTP, WebSocket, and other
transport mechanisms.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
import json
import aiohttp
import ssl
import base64

from qcc.common.models import Cell

logger = logging.getLogger(__name__)

class ProtocolHandler:
    """
    Base class for protocol handlers.
    
    Protocol handlers are responsible for the actual delivery of cells
    to assemblers using specific transport protocols.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the protocol handler.
        
        Args:
            config: Protocol-specific configuration
        """
        self.config = config or {}
        self.stats = {
            "delivery_attempts": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "total_delivery_time_ms": 0,
            "average_delivery_time_ms": 0
        }
    
    async def deliver_cell(
        self,
        cell: Cell,
        assembler_id: str,
        quantum_signature: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Deliver a cell to an assembler.
        
        Args:
            cell: The cell to deliver
            assembler_id: The ID of the target assembler
            quantum_signature: Quantum signature for verification
            options: Protocol-specific delivery options
            
        Returns:
            Delivery result details
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement deliver_cell method")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this protocol handler.
        
        Returns:
            Protocol handler statistics
        """
        return self.stats
    
    def _update_stats(self, delivery_time_ms: float, success: bool):
        """
        Update protocol handler statistics.
        
        Args:
            delivery_time_ms: Time taken for delivery in milliseconds
            success: Whether the delivery was successful
        """
        self.stats["delivery_attempts"] += 1
        
        if success:
            self.stats["successful_deliveries"] += 1
        else:
            self.stats["failed_deliveries"] += 1
        
        self.stats["total_delivery_time_ms"] += delivery_time_ms
        
        if self.stats["successful_deliveries"] > 0:
            self.stats["average_delivery_time_ms"] = (
                self.stats["total_delivery_time_ms"] / 
                self.stats["successful_deliveries"]
            )

class HTTPProtocolHandler(ProtocolHandler):
    """
    Protocol handler for delivering cells via HTTP/HTTPS.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the HTTP protocol handler.
        
        Args:
            config: HTTP-specific configuration
        """
        super().__init__(config)
        
        # Create HTTP session
        self.session = None
        self.timeout = aiohttp.ClientTimeout(
            total=self.config.get("timeout_seconds", 60)
        )
        
        # SSL context
        self.ssl_context = None
        verify_ssl = self.config.get("verify_ssl", True)
        
        if not verify_ssl:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL certificate verification is disabled for HTTP protocol handler")
    
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def deliver_cell(
        self,
        cell: Cell,
        assembler_id: str,
        quantum_signature: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Deliver a cell to an assembler via HTTP/HTTPS.
        
        Args:
            cell: The cell to deliver
            assembler_id: The ID of the target assembler
            quantum_signature: Quantum signature for verification
            options: HTTP-specific delivery options
            
        Returns:
            Delivery result details
        """
        options = options or {}
        
        # Ensure session is created
        await self._ensure_session()
        
        # Get the assembler's HTTP endpoint
        endpoint = options.get("endpoint")
        if not endpoint:
            # In a real implementation, there would be a lookup service to find the assembler's endpoint
            # For this example, we'll use a placeholder URL
            endpoint = f"https://assembler-{assembler_id}.cellcomputing.ai/api/v1/cells"
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "QCC-Provider/1.0",
            "X-QCC-Assembler-ID": assembler_id,
            "X-QCC-Provider-ID": self.config.get("provider_id", "default-provider"),
            "X-QCC-Quantum-Signature": quantum_signature
        }
        
        # Add custom headers from options
        custom_headers = options.get("headers", {})
        headers.update(custom_headers)
        
        # Convert cell to JSON for sending
        cell_data = cell.to_dict()
        
        # Start timing
        start_time = time.time()
        
        try:
            # Send cell to assembler
            async with self.session.post(
                endpoint,
                json=cell_data,
                headers=headers,
                ssl=self.ssl_context
            ) as response:
                # Calculate delivery time
                delivery_time_ms = (time.time() - start_time) * 1000
                
                # Process response
                response_data = await response.json()
                success = response.status in (200, 201, 202)
                
                # Update statistics
                self._update_stats(delivery_time_ms, success)
                
                if not success:
                    logger.error(f"HTTP delivery failed with status {response.status}: {response_data}")
                    return {
                        "success": False,
                        "status_code": response.status,
                        "error": f"HTTP delivery failed with status {response.status}",
                        "response": response_data,
                        "delivery_time_ms": delivery_time_ms
                    }
                
                return {
                    "success": True,
                    "status_code": response.status,
                    "response": response_data,
                    "delivery_time_ms": delivery_time_ms
                }
                
        except aiohttp.ClientError as e:
            # Calculate delivery time even for failures
            delivery_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(delivery_time_ms, False)
            
            logger.error(f"HTTP delivery error: {e}")
            return {
                "success": False,
                "error": f"HTTP client error: {str(e)}",
                "delivery_time_ms": delivery_time_ms
            }
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

class WSProtocolHandler(ProtocolHandler):
    """
    Protocol handler for delivering cells via WebSockets.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the WebSocket protocol handler.
        
        Args:
            config: WebSocket-specific configuration
        """
        super().__init__(config)
        
        # Connection pool for WebSocket connections
        self.connections = {}
        
        # SSL context
        self.ssl_context = None
        verify_ssl = self.config.get("verify_ssl", True)
        
        if not verify_ssl:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL certificate verification is disabled for WebSocket protocol handler")
    
    async def deliver_cell(
        self,
        cell: Cell,
        assembler_id: str,
        quantum_signature: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Deliver a cell to an assembler via WebSocket.
        
        Args:
            cell: The cell to deliver
            assembler_id: The ID of the target assembler
            quantum_signature: Quantum signature for verification
            options: WebSocket-specific delivery options
            
        Returns:
            Delivery result details
        """
        options = options or {}
        
        # Get the assembler's WebSocket endpoint
        endpoint = options.get("endpoint")
        if not endpoint:
            # In a real implementation, there would be a lookup service to find the assembler's endpoint
            # For this example, we'll use a placeholder URL
            endpoint = f"wss://assembler-{assembler_id}.cellcomputing.ai/api/v1/ws"
        
        # Start timing
        start_time = time.time()
        
        try:
            # Get or create WebSocket connection
            ws = await self._get_connection(assembler_id, endpoint, quantum_signature)
            
            # Prepare cell data
            message = {
                "type": "cell_delivery",
                "cell": cell.to_dict(),
                "quantum_signature": quantum_signature,
                "timestamp": time.time(),
                "delivery_id": options.get("delivery_id", str(time.time()))
            }
            
            # Send cell data
            await ws.send_json(message)
            
            # Wait for acknowledgement
            ack_timeout = self.config.get("ack_timeout_seconds", 10)
            response = await asyncio.wait_for(ws.receive_json(), timeout=ack_timeout)
            
            # Calculate delivery time
            delivery_time_ms = (time.time() - start_time) * 1000
            
            # Check acknowledgement
            if response.get("type") != "ack" or response.get("delivery_id") != message["delivery_id"]:
                # Update statistics
                self._update_stats(delivery_time_ms, False)
                
                logger.error(f"WebSocket delivery failed: invalid acknowledgement")
                return {
                    "success": False,
                    "error": "Invalid acknowledgement received",
                    "response": response,
                    "delivery_time_ms": delivery_time_ms
                }
            
            # Update statistics
            self._update_stats(delivery_time_ms, True)
            
            return {
                "success": True,
                "delivery_id": message["delivery_id"],
                "response": response,
                "delivery_time_ms": delivery_time_ms
            }
            
        except asyncio.TimeoutError:
            # Calculate delivery time for timeout
            delivery_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(delivery_time_ms, False)
            
            logger.error(f"WebSocket delivery timed out after {delivery_time_ms}ms")
            return {
                "success": False,
                "error": "Acknowledgement timed out",
                "delivery_time_ms": delivery_time_ms
            }
            
        except Exception as e:
            # Calculate delivery time for errors
            delivery_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(delivery_time_ms, False)
            
            logger.error(f"WebSocket delivery error: {e}")
            return {
                "success": False,
                "error": f"WebSocket error: {str(e)}",
                "delivery_time_ms": delivery_time_ms
            }
    
    async def _get_connection(self, assembler_id: str, endpoint: str, quantum_signature: str):
        """
        Get or create a WebSocket connection to an assembler.
        
        Args:
            assembler_id: The ID of the assembler
            endpoint: The WebSocket endpoint
            quantum_signature: Quantum signature for authentication
            
        Returns:
            WebSocket connection
        """
        # Check for existing connection
        if assembler_id in self.connections:
            ws = self.connections[assembler_id]
            
            # Check if connection is still open
            if not ws.closed:
                return ws
            
            # Remove closed connection
            del self.connections[assembler_id]
        
        # Create new connection
        headers = {
            "X-QCC-Assembler-ID": assembler_id,
            "X-QCC-Provider-ID": self.config.get("provider_id", "default-provider"),
            "X-QCC-Quantum-Signature": quantum_signature
        }
        
        ws = await aiohttp.ClientSession().ws_connect(
            endpoint,
            headers=headers,
            ssl=self.ssl_context,
            heartbeat=self.config.get("heartbeat_interval_seconds", 30)
        )
        
        # Store connection
        self.connections[assembler_id] = ws
        
        return ws
    
    async def close(self):
        """Close all WebSocket connections."""
        for ws in self.connections.values():
            await ws.close()
        
        self.connections = {}

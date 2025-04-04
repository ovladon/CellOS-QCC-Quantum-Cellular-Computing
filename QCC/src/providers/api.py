"""
Provider API implementation for Quantum Cellular Computing.

This module defines the API interface for cell providers, which are
responsible for maintaining repositories of cells and responding to
assembler requests for cells with specific capabilities.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import hashlib
import aiohttp
from aiohttp import web

from qcc.providers.repository import CellRepository
from qcc.providers.distribution import CellDistributor
from qcc.providers.verification import CellVerifier
from qcc.common.models import Cell, CellConfiguration
from qcc.common.exceptions import CellRequestError, VerificationError, DistributionError

logger = logging.getLogger(__name__)

class ProviderAPI:
    """
    API interface for the Cell Provider service.
    
    The Provider API handles requests from assemblers for cells with specific
    capabilities, delivers requested cells, and manages the cell repository.
    
    Attributes:
        provider_id (str): Unique identifier for this provider
        repository (CellRepository): Repository of available cells
        distributor (CellDistributor): Component for delivering cells
        verifier (CellVerifier): Component for verifying cell integrity
        capabilities (Dict[str, List[str]]): Map of capabilities to cell types
        active_cells (Dict[str, Dict]): Tracking for distributed cells
        app (web.Application): AIOHTTP web application
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Provider API.
        
        Args:
            config: Configuration dictionary
        """
        self.provider_id = str(uuid.uuid4())
        self.config = config or {}
        
        # Initialize components
        self.repository = CellRepository(config.get("repository", {}))
        self.distributor = CellDistributor(config.get("distribution", {}))
        self.verifier = CellVerifier(config.get("verification", {}))
        
        # Track capabilities and active cells
        self.capabilities = {}
        self.active_cells = {}
        
        # Performance metrics
        self.total_requests = 0
        self.total_cells_delivered = 0
        self.response_times = []
        
        # Create web application
        self.app = web.Application()
        self._setup_routes()
        
        logger.info(f"Provider API initialized with ID {self.provider_id}")
    
    def _setup_routes(self):
        """Configure API routes for the provider service."""
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/status', self.handle_status)
        self.app.router.add_get('/capabilities', self.handle_capabilities)
        
        # Cell request endpoints
        self.app.router.add_post('/cells/request', self.handle_cell_request)
        self.app.router.add_get('/cells/{cell_id}', self.handle_get_cell)
        self.app.router.add_post('/cells/{cell_id}/release', self.handle_release_cell)
        
        # Cell management endpoints
        self.app.router.add_post('/admin/cells/register', self.handle_register_cell)
        self.app.router.add_post('/admin/cells/{cell_id}/update', self.handle_update_cell)
        self.app.router.add_delete('/admin/cells/{cell_id}', self.handle_remove_cell)
        
        # Authentication middleware
        self.app.middlewares.append(self._auth_middleware)
        
        logger.debug("API routes configured")
    
    @web.middleware
    async def _auth_middleware(self, request, handler):
        """
        Authentication middleware for API requests.
        
        Args:
            request: HTTP request
            handler: Request handler function
            
        Returns:
            HTTP response
        """
        # Skip authentication for public endpoints
        if request.path in ['/', '/status', '/capabilities']:
            return await handler(request)
        
        # Check if authentication is required in config
        if not self.config.get("auth_required", False):
            return await handler(request)
        
        # Check for API key in header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return web.json_response({
                "status": "error",
                "message": "Missing API key"
            }, status=401)
        
        # Validate API key (simplified implementation)
        valid_keys = self.config.get("api_keys", [])
        if api_key not in valid_keys:
            logger.warning(f"Invalid API key attempted from {request.remote}")
            return web.json_response({
                "status": "error",
                "message": "Invalid API key"
            }, status=401)
        
        # Continue to handler
        return await handler(request)
    
    async def handle_root(self, request):
        """
        Handle requests to the root endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with provider information
        """
        return web.json_response({
            "provider_id": self.provider_id,
            "name": self.config.get("name", "QCC Cell Provider"),
            "version": self.config.get("version", "1.0.0"),
            "description": self.config.get("description", "Quantum Cellular Computing Cell Provider"),
            "documentation": self.config.get("documentation_url", "https://docs.cellcomputing.ai/provider-api"),
            "capabilities_url": f"{request.url.scheme}://{request.url.host}:{request.url.port}/capabilities"
        })
    
    async def handle_status(self, request):
        """
        Handle requests to the status endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with provider status
        """
        # Get repository status
        repo_status = await self.repository.get_status()
        
        # Calculate average response time
        avg_response_time = 0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
        
        return web.json_response({
            "status": "active",
            "provider_id": self.provider_id,
            "cells_available": repo_status.get("total_cells", 0),
            "capabilities_count": len(self.capabilities),
            "active_cells": len(self.active_cells),
            "total_requests": self.total_requests,
            "total_cells_delivered": self.total_cells_delivered,
            "avg_response_time_ms": avg_response_time,
            "uptime_seconds": repo_status.get("uptime_seconds", 0)
        })
    
    async def handle_capabilities(self, request):
        """
        Handle requests to the capabilities endpoint.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with available capabilities
        """
        # Get capabilities from repository
        capabilities = await self.repository.get_capabilities()
        
        # Update local cache
        self.capabilities = capabilities
        
        # Format response
        formatted_capabilities = []
        for capability, cell_types in capabilities.items():
            formatted_capabilities.append({
                "name": capability,
                "description": self.repository.get_capability_description(capability),
                "cell_types": len(cell_types),
                "versions": self.repository.get_capability_versions(capability)
            })
        
        return web.json_response({
            "capabilities": formatted_capabilities,
            "total_count": len(formatted_capabilities)
        })
    
    async def handle_cell_request(self, request):
        """
        Handle cell request from an assembler.
        
        Args:
            request: HTTP request with capability requirements
            
        Returns:
            HTTP response with cell information or error
        """
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Parse request body
            body = await request.json()
            
            # Validate request
            if "capability" not in body and "cell_type" not in body:
                return web.json_response({
                    "status": "error",
                    "message": "Request must include either 'capability' or 'cell_type'"
                }, status=400)
            
            quantum_signature = body.get("quantum_signature")
            if not quantum_signature:
                return web.json_response({
                    "status": "error",
                    "message": "Missing quantum signature"
                }, status=400)
            
            # Handle cell type specific request
            if "cell_type" in body:
                cell_type = body["cell_type"]
                version = body.get("version", "latest")
                
                logger.info(f"Cell request for specific type: {cell_type} version {version}")
                
                # Get cell from repository
                try:
                    cell = await self.repository.get_cell_by_type(
                        cell_type=cell_type,
                        version=version
                    )
                except Exception as e:
                    logger.error(f"Failed to get cell by type: {e}")
                    return web.json_response({
                        "status": "error",
                        "message": f"Cell type not available: {cell_type}"
                    }, status=404)
                
            # Handle capability-based request
            else:
                capability = body["capability"]
                parameters = body.get("parameters", {})
                context = body.get("context", {})
                
                logger.info(f"Cell request for capability: {capability}")
                
                # Get best matching cell for the capability
                try:
                    cell = await self.repository.get_cell_for_capability(
                        capability=capability,
                        parameters=parameters,
                        context=context
                    )
                except Exception as e:
                    logger.error(f"Failed to get cell for capability: {e}")
                    return web.json_response({
                        "status": "error",
                        "message": f"Capability not available: {capability}"
                    }, status=404)
            
            # Verify the cell
            try:
                verification_result = await self.verifier.verify_cell(
                    cell=cell,
                    quantum_signature=quantum_signature
                )
                
                if not verification_result["verified"]:
                    logger.warning(f"Cell verification failed: {verification_result['reason']}")
                    return web.json_response({
                        "status": "error",
                        "message": f"Cell verification failed: {verification_result['reason']}"
                    }, status=403)
                    
            except VerificationError as e:
                logger.error(f"Verification error: {e}")
                return web.json_response({
                    "status": "error",
                    "message": f"Verification error: {str(e)}"
                }, status=500)
            
            # Prepare cell for distribution
            try:
                distribution_result = await self.distributor.prepare_cell(
                    cell=cell,
                    quantum_signature=quantum_signature,
                    context=body.get("context", {})
                )
                
                if not distribution_result["success"]:
                    logger.warning(f"Cell preparation failed: {distribution_result['reason']}")
                    return web.json_response({
                        "status": "error",
                        "message": f"Cell preparation failed: {distribution_result['reason']}"
                    }, status=500)
                    
            except DistributionError as e:
                logger.error(f"Distribution error: {e}")
                return web.json_response({
                    "status": "error",
                    "message": f"Distribution error: {str(e)}"
                }, status=500)
            
            # Generate cell ID
            cell_id = str(uuid.uuid4())
            
            # Add quantum signature to cell
            cell_data = cell.copy()
            cell_data["id"] = cell_id
            cell_data["quantum_signature"] = quantum_signature
            cell_data["provider"] = self.provider_id
            cell_data["created_at"] = datetime.now().isoformat()
            cell_data["status"] = "initialized"
            
            # Store active cell
            self.active_cells[cell_id] = {
                "cell": cell_data,
                "quantum_signature": quantum_signature,
                "requested_at": datetime.now().isoformat(),
                "assembler_id": body.get("assembler_id", "unknown")
            }
            
            # Increment delivery counter
            self.total_cells_delivered += 1
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            self.response_times.append(response_time_ms)
            # Keep only the last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            # Return cell information
            return web.json_response({
                "status": "success",
                "cell_id": cell_id,
                "download_url": f"{request.url.scheme}://{request.url.host}:{request.url.port}/cells/{cell_id}",
                "cell_type": cell_data.get("cell_type"),
                "capability": cell_data.get("capability"),
                "version": cell_data.get("version"),
                "expiration": datetime.now().timestamp() + self.config.get("cell_expiration_seconds", 3600)
            })
            
        except Exception as e:
            logger.error(f"Error handling cell request: {e}", exc_info=True)
            return web.json_response({
                "status": "error",
                "message": f"Internal server error: {str(e)}"
            }, status=500)
    
    async def handle_get_cell(self, request):
        """
        Handle request to download a specific cell.
        
        Args:
            request: HTTP request with cell ID
            
        Returns:
            HTTP response with cell package or error
        """
        cell_id = request.match_info.get("cell_id")
        
        # Check if cell exists
        if cell_id not in self.active_cells:
            return web.json_response({
                "status": "error",
                "message": f"Cell not found: {cell_id}"
            }, status=404)
        
        cell_data = self.active_cells[cell_id]["cell"]
        
        # Get cell package from distributor
        try:
            package = await self.distributor.get_cell_package(cell_data)
            
            # Return cell package
            return web.json_response({
                "status": "success",
                "cell_id": cell_id,
                "quantum_signature": cell_data["quantum_signature"],
                "package": package
            })
            
        except DistributionError as e:
            logger.error(f"Error getting cell package: {e}")
            return web.json_response({
                "status": "error",
                "message": f"Distribution error: {str(e)}"
            }, status=500)
    
    async def handle_release_cell(self, request):
        """
        Handle request to release a cell.
        
        Args:
            request: HTTP request with cell ID
            
        Returns:
            HTTP response with success or error
        """
        cell_id = request.match_info.get("cell_id")
        
        # Check if cell exists
        if cell_id not in self.active_cells:
            return web.json_response({
                "status": "error",
                "message": f"Cell not found: {cell_id}"
            }, status=404)
        
        # Parse request body
        body = await request.json()
        
        # Validate quantum signature
        expected_signature = self.active_cells[cell_id]["quantum_signature"]
        provided_signature = body.get("quantum_signature")
        
        if not provided_signature or provided_signature != expected_signature:
            return web.json_response({
                "status": "error",
                "message": "Invalid quantum signature"
            }, status=403)
        
        # Update usage metrics
        usage_metrics = body.get("usage_metrics", {})
        self.active_cells[cell_id]["usage_metrics"] = usage_metrics
        self.active_cells[cell_id]["released_at"] = datetime.now().isoformat()
        
        # Remove from active cells (or mark as released)
        if self.config.get("retain_released_cells", False):
            self.active_cells[cell_id]["status"] = "released"
        else:
            del self.active_cells[cell_id]
        
        return web.json_response({
            "status": "success",
            "message": f"Cell {cell_id} released successfully"
        })
    
    async def handle_register_cell(self, request):
        """
        Handle request to register a new cell.
        
        Args:
            request: HTTP request with cell data
            
        Returns:
            HTTP response with success or error
        """
        try:
            # Parse request body
            body = await request.json()
            
            # Validate cell data
            if "cell_type" not in body or "capability" not in body:
                return web.json_response({
                    "status": "error",
                    "message": "Missing required fields: cell_type and capability"
                }, status=400)
            
            # Check for existing cell
            existing_cell = await self.repository.get_cell_by_type(
                cell_type=body["cell_type"],
                version=body.get("version", "latest"),
                raise_error=False
            )
            
            if existing_cell and not body.get("force_update", False):
                return web.json_response({
                    "status": "error",
                    "message": f"Cell already exists: {body['cell_type']} version {body.get('version', 'latest')}",
                    "cell_id": existing_cell.get("id")
                }, status=409)
            
            # Verify cell package
            verification_result = await self.verifier.verify_package(
                package=body.get("package", {}),
                metadata=body
            )
            
            if not verification_result["verified"]:
                return web.json_response({
                    "status": "error",
                    "message": f"Package verification failed: {verification_result['reason']}"
                }, status=400)
            
            # Register cell in repository
            cell_id = await self.repository.register_cell(
                cell_type=body["cell_type"],
                capability=body["capability"],
                version=body.get("version", "1.0.0"),
                package=body.get("package", {}),
                metadata=body.get("metadata", {})
            )
            
            # Update capabilities cache
            await self.repository.get_capabilities()
            
            return web.json_response({
                "status": "success",
                "message": "Cell registered successfully",
                "cell_id": cell_id
            })
            
        except Exception as e:
            logger.error(f"Error registering cell: {e}", exc_info=True)
            return web.json_response({
                "status": "error",
                "message": f"Cell registration failed: {str(e)}"
            }, status=500)
    
    async def handle_update_cell(self, request):
        """
        Handle request to update an existing cell.
        
        Args:
            request: HTTP request with cell updates
            
        Returns:
            HTTP response with success or error
        """
        cell_id = request.match_info.get("cell_id")
        
        try:
            # Parse request body
            body = await request.json()
            
            # Check if cell exists
            cell = await self.repository.get_cell_by_id(cell_id)
            if not cell:
                return web.json_response({
                    "status": "error",
                    "message": f"Cell not found: {cell_id}"
                }, status=404)
            
            # Update cell
            updated_cell = await self.repository.update_cell(
                cell_id=cell_id,
                updates=body
            )
            
            return web.json_response({
                "status": "success",
                "message": "Cell updated successfully",
                "cell_id": cell_id,
                "version": updated_cell.get("version")
            })
            
        except Exception as e:
            logger.error(f"Error updating cell: {e}", exc_info=True)
            return web.json_response({
                "status": "error",
                "message": f"Cell update failed: {str(e)}"
            }, status=500)
    
    async def handle_remove_cell(self, request):
        """
        Handle request to remove a cell.
        
        Args:
            request: HTTP request with cell ID
            
        Returns:
            HTTP response with success or error
        """
        cell_id = request.match_info.get("cell_id")
        
        try:
            # Check if cell exists
            cell = await self.repository.get_cell_by_id(cell_id)
            if not cell:
                return web.json_response({
                    "status": "error",
                    "message": f"Cell not found: {cell_id}"
                }, status=404)
            
            # Check if cell is in use
            active_instances = [c for c_id, c in self.active_cells.items() 
                               if c["cell"].get("cell_type") == cell.get("cell_type")]
            
            if active_instances and not request.query.get("force", "false").lower() == "true":
                return web.json_response({
                    "status": "error",
                    "message": f"Cell is currently in use ({len(active_instances)} active instances)",
                    "active_count": len(active_instances)
                }, status=409)
            
            # Remove cell
            result = await self.repository.remove_cell(cell_id)
            
            return web.json_response({
                "status": "success",
                "message": "Cell removed successfully",
                "cell_id": cell_id
            })
            
        except Exception as e:
            logger.error(f"Error removing cell: {e}", exc_info=True)
            return web.json_response({
                "status": "error",
                "message": f"Cell removal failed: {str(e)}"
            }, status=500)
    
    async def start(self, host: str = "0.0.0.0", port: int = 8081):
        """
        Start the Provider API server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        # Initialize repository
        await self.repository.initialize()
        
        # Initialize distributor
        await self.distributor.initialize()
        
        # Start cleanup task
        asyncio.create_task(self._cell_cleanup_task())
        
        # Start server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Provider API server started on http://{host}:{port}")
        
        return site
    
    async def _cell_cleanup_task(self):
        """Background task to clean up expired cells."""
        while True:
            try:
                # Get current time
                now = datetime.now()
                
                # Find expired cells
                expiration_seconds = self.config.get("cell_expiration_seconds", 3600)
                expired_cells = []
                
                for cell_id, cell_info in self.active_cells.items():
                    requested_at = datetime.fromisoformat(cell_info["requested_at"])
                    if (now - requested_at).total_seconds() > expiration_seconds:
                        expired_cells.append(cell_id)
                
                # Remove expired cells
                for cell_id in expired_cells:
                    logger.info(f"Cleaning up expired cell: {cell_id}")
                    self.active_cells[cell_id]["status"] = "expired"
                    
                    if not self.config.get("retain_expired_cells", False):
                        del self.active_cells[cell_id]
                
                # Sleep for cleanup interval
                await asyncio.sleep(self.config.get("cleanup_interval_seconds", 300))
                
            except Exception as e:
                logger.error(f"Error in cell cleanup task: {e}", exc_info=True)
                await asyncio.sleep(60)  # Sleep for a minute on error

# Convenience function to create and configure a provider API
async def create_provider_api(config_path: str = None) -> ProviderAPI:
    """
    Create and configure a Provider API instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured ProviderAPI instance
    """
    # Load configuration
    config = {}
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            logger.warning("Using default configuration")
    
    # Create provider API
    provider_api = ProviderAPI(config)
    
    return provider_api

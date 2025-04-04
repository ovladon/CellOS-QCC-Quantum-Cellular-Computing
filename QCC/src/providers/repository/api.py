"""
API interface for the QCC repository.

This module provides the HTTP API for interacting with the cell repository,
including endpoints for browsing, searching, retrieving, and publishing cells.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from aiohttp import web

from qcc.common.exceptions import (
    RepositoryError, AuthenticationError, AuthorizationError,
    ValidationError, CellNotFoundError
)
from qcc.providers.repository.repository import CellRepository
from qcc.providers.repository.authentication import AuthManager

logger = logging.getLogger(__name__)

class RepositoryAPI:
    """
    Provides HTTP API endpoints for the cell repository.
    
    This class implements the RESTful API for interacting with the repository,
    handling authentication, request validation, and response formatting.
    """
    
    def __init__(self, repository: CellRepository, auth_manager: AuthManager, host: str = "localhost", port: int = 8080):
        """
        Initialize the repository API.
        
        Args:
            repository: Cell repository instance
            auth_manager: Authentication manager
            host: Host to bind the API server
            port: Port to bind the API server
        """
        self.repository = repository
        self.auth_manager = auth_manager
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up API routes."""
        # Authentication routes
        self.app.router.add_post('/api/auth/login', self.handle_login)
        self.app.router.add_post('/api/auth/token', self.handle_token_auth)
        
        # API key management
        self.app.router.add_post('/api/auth/api-keys', self.handle_create_api_key)
        self.app.router.add_get('/api/auth/api-keys', self.handle_list_api_keys)
        self.app.router.add_delete('/api/auth/api-keys/{key_id}', self.handle_revoke_api_key)
        
        # Cell routes
        self.app.router.add_get('/api/cells', self.handle_list_cells)
        self.app.router.add_get('/api/cells/{cell_id}', self.handle_get_cell)
        self.app.router.add_get('/api/cells/{cell_id}/versions', self.handle_list_cell_versions)
        self.app.router.add_get('/api/cells/{cell_id}/versions/{version}', self.handle_get_cell_version)
        self.app.router.add_post('/api/cells', self.handle_register_cell)
        self.app.router.add_put('/api/cells/{cell_id}', self.handle_update_cell)
        self.app.router.add_delete('/api/cells/{cell_id}', self.handle_delete_cell)
        self.app.router.add_delete('/api/cells/{cell_id}/versions/{version}', self.handle_delete_cell_version)
        
        # Search routes
        self.app.router.add_get('/api/search', self.handle_search)
        self.app.router.add_get('/api/capabilities', self.handle_list_capabilities)
        
        # Repository management routes
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_post('/api/rebuild-index', self.handle_rebuild_index)
        
        # Add CORS middleware
        self.app.middlewares.append(self._cors_middleware)
        
        # Add error handling middleware
        self.app.middlewares.append(self._error_middleware)
    
    @web.middleware
    async def _cors_middleware(self, request, handler):
        """Middleware to handle CORS."""
        resp = await handler(request)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    
    @web.middleware
    async def _error_middleware(self, request, handler):
        """Middleware to handle errors."""
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except AuthenticationError as e:
            return self._error_response(401, str(e) or "Authentication required")
        except AuthorizationError as e:
            return self._error_response(403, str(e) or "Not authorized")
        except CellNotFoundError as e:
            return self._error_response(404, str(e) or "Cell not found")
        except ValidationError as e:
            return self._error_response(400, str(e) or "Validation failed")
        except Exception as e:
            logger.error(f"Unhandled error in API: {e}", exc_info=True)
            return self._error_response(500, "Internal server error")
    
    async def handle_login(self, request):
        """Handle user login request."""
        try:
            data = await request.json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return self._error_response(400, "Username and password are required")
                
            token = await self.auth_manager.authenticate_user(username, password)
            
            return web.json_response({
                "token": token,
                "token_type": "Bearer"
            })
            
        except AuthenticationError as e:
            return self._error_response(401, str(e))
        except Exception as e:
            logger.error(f"Login error: {e}")
            return self._error_response(500, "Login failed")
    
    async def handle_token_auth(self, request):
        """Handle token-based authentication request."""
        try:
            data = await request.json()
            api_key_id = data.get('api_key_id')
            api_key_secret = data.get('api_key_secret')
            
            if not api_key_id or not api_key_secret:
                return self._error_response(400, "API key ID and secret are required")
                
            token = await self.auth_manager.authenticate_service(api_key_id, api_key_secret)
            
            return web.json_response({
                "token": token,
                "token_type": "Bearer"
            })
            
        except AuthenticationError as e:
            return self._error_response(401, str(e))
        except Exception as e:
            logger.error(f"Token auth error: {e}")
            return self._error_response(500, "Authentication failed")
    
    async def handle_create_api_key(self, request):
        """Handle API key creation request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            token_data = await self.auth_manager.verify_token(token)
            user_id = token_data.get("user_id")
            
            has_permission = await self.auth_manager.check_permission(token, "create_api_key")
            if not has_permission:
                raise AuthorizationError("Not authorized to create API keys")
                
            # Parse request
            data = await request.json()
            permissions = data.get('permissions', ['read'])
            expiry_days = data.get('expiry_days', 365)
            
            # Create API key
            key_data = await self.auth_manager.create_api_key(
                owner=user_id,
                permissions=permissions,
                expiry_days=expiry_days
            )
            
            return web.json_response(key_data)
            
        except (AuthenticationError, AuthorizationError) as e:
            raise
        except Exception as e:
            logger.error(f"API key creation error: {e}")
            return self._error_response(500, "Failed to create API key")
    
    async def handle_list_api_keys(self, request):
        """Handle API key listing request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            token_data = await self.auth_manager.verify_token(token)
            user_id = token_data.get("user_id")
            
            # List API keys
            keys = await self.auth_manager.list_api_keys(user_id)
            
            return web.json_response({
                "api_keys": keys
            })
            
        except AuthenticationError as e:
            raise
        except Exception as e:
            logger.error(f"API key listing error: {e}")
            return self._error_response(500, "Failed to list API keys")
    
    async def handle_revoke_api_key(self, request):
        """Handle API key revocation request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            token_data = await self.auth_manager.verify_token(token)
            user_id = token_data.get("user_id")
            
            # Get key ID from path
            key_id = request.match_info.get('key_id')
            if not key_id:
                return self._error_response(400, "API key ID is required")
                
            # Revoke API key
            success = await self.auth_manager.revoke_api_key(key_id, user_id)
            
            if not success:
                return self._error_response(404, "API key not found")
                
            return web.json_response({
                "success": True,
                "message": "API key revoked"
            })
            
        except (AuthenticationError, AuthorizationError) as e:
            raise
        except Exception as e:
            logger.error(f"API key revocation error: {e}")
            return self._error_response(500, "Failed to revoke API key")
    
    async def handle_list_cells(self, request):
        """Handle cell listing request."""
        try:
            # Parse query parameters
            limit = int(request.query.get('limit', 100))
            offset = int(request.query.get('offset', 0))
            tags = request.query.get('tags')
            cell_type = request.query.get('type')
            
            # Parse tags
            tag_list = tags.split(',') if tags else None
            
            # List cells
            cells = await self.repository.list_cells(
                limit=limit,
                offset=offset,
                tags=tag_list,
                cell_type=cell_type
            )
            
            # Get total count
            total_count = await self.repository.count_cells(
                tags=tag_list,
                cell_type=cell_type
            )
            
            return web.json_response({
                "cells": cells,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            })
            
        except Exception as e:
            logger.error(f"Cell listing error: {e}")
            return self._error_response(500, "Failed to list cells")
    
    async def handle_get_cell(self, request):
        """Handle cell retrieval request."""
        try:
            # Get cell ID from path
            cell_id = request.match_info.get('cell_id')
            
            # Get cell info
            cell_info = await self.repository.get_cell_info(cell_id)
            
            if not cell_info:
                raise CellNotFoundError(f"Cell not found: {cell_id}")
                
            return web.json_response(cell_info)
            
        except CellNotFoundError as e:
            raise
        except Exception as e:
            logger.error(f"Cell retrieval error: {e}")
            return self._error_response(500, "Failed to retrieve cell")
    
    async def handle_list_cell_versions(self, request):
        """Handle cell version listing request."""
        try:
            # Get cell ID from path
            cell_id = request.match_info.get('cell_id')
            
            # List versions
            versions = await self.repository.list_cell_versions(cell_id)
            
            return web.json_response({
                "cell_id": cell_id,
                "versions": versions
            })
            
        except CellNotFoundError as e:
            raise
        except Exception as e:
            logger.error(f"Cell version listing error: {e}")
            return self._error_response(500, "Failed to list cell versions")
    
    async def handle_get_cell_version(self, request):
        """Handle cell version retrieval request."""
        try:
            # Get cell ID and version from path
            cell_id = request.match_info.get('cell_id')
            version = request.match_info.get('version')
            
            # Parse query parameters
            include_code = request.query.get('include_code', 'false').lower() == 'true'
            
            # Get cell data
            cell_data = await self.repository.get_cell(
                cell_id=cell_id,
                version=version,
                include_code=include_code
            )
            
            if not cell_data:
                raise CellNotFoundError(f"Cell version not found: {cell_id} v{version}")
                
            return web.json_response(cell_data)
            
        except CellNotFoundError as e:
            raise
        except Exception as e:
            logger.error(f"Cell version retrieval error: {e}")
            return self._error_response(500, "Failed to retrieve cell version")
    
    async def handle_register_cell(self, request):
        """Handle cell registration request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            has_permission = await self.auth_manager.check_permission(token, "register_cell")
            if not has_permission:
                raise AuthorizationError("Not authorized to register cells")
                
            # Parse request
            cell_data = await request.json()
            
            # Register cell
            result = await self.repository.register_cell(cell_data)
            
            return web.json_response({
                "success": True,
                "cell_id": result.get("cell_id"),
                "version": result.get("version")
            })
            
        except (AuthenticationError, AuthorizationError, ValidationError) as e:
            raise
        except Exception as e:
            logger.error(f"Cell registration error: {e}")
            return self._error_response(500, "Failed to register cell")
    
    async def handle_update_cell(self, request):
        """Handle cell update request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            has_permission = await self.auth_manager.check_permission(token, "update_cell")
            if not has_permission:
                raise AuthorizationError("Not authorized to update cells")
                
            # Get cell ID from path
            cell_id = request.match_info.get('cell_id')
            
            # Parse request
            cell_data = await request.json()
            
            # Check if cell ID in path matches manifest
            manifest_cell_id = cell_data.get("manifest", {}).get("id")
            if manifest_cell_id and manifest_cell_id != cell_id:
                return self._error_response(400, "Cell ID in path doesn't match manifest")
                
            # Update manifest ID if not present
            if not manifest_cell_id:
                if "manifest" not in cell_data:
                    cell_data["manifest"] = {}
                cell_data["manifest"]["id"] = cell_id
            
            # Update cell
            result = await self.repository.update_cell(cell_data)
            
            return web.json_response({
                "success": True,
                "cell_id": result.get("cell_id"),
                "version": result.get("version")
            })
            
        except (AuthenticationError, AuthorizationError, ValidationError, CellNotFoundError) as e:
            raise
        except Exception as e:
            logger.error(f"Cell update error: {e}")
            return self._error_response(500, "Failed to update cell")
    
    async def handle_delete_cell(self, request):
        """Handle cell deletion request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            has_permission = await self.auth_manager.check_permission(token, "delete_cell")
            if not has_permission:
                raise AuthorizationError("Not authorized to delete cells")
                
            # Get cell ID from path
            cell_id = request.match_info.get('cell_id')
            
            # Delete cell
            success = await self.repository.delete_cell(cell_id)
            
            if not success:
                raise CellNotFoundError(f"Cell not found: {cell_id}")
                
            return web.json_response({
                "success": True,
                "message": f"Cell {cell_id} deleted"
            })
            
        except (AuthenticationError, AuthorizationError, CellNotFoundError) as e:
            raise
        except Exception as e:
            logger.error(f"Cell deletion error: {e}")
            return self._error_response(500, "Failed to delete cell")
    
    async def handle_delete_cell_version(self, request):
        """Handle cell version deletion request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            has_permission = await self.auth_manager.check_permission(token, "delete_cell_version")
            if not has_permission:
                raise AuthorizationError("Not authorized to delete cell versions")
                
            # Get cell ID and version from path
            cell_id = request.match_info.get('cell_id')
            version = request.match_info.get('version')
            
            # Delete cell version
            success = await self.repository.delete_cell_version(cell_id, version)
            
            if not success:
                raise CellNotFoundError(f"Cell version not found: {cell_id} v{version}")
                
            return web.json_response({
                "success": True,
                "message": f"Cell {cell_id} version {version} deleted"
            })
            
        except (AuthenticationError, AuthorizationError, CellNotFoundError) as e:
            raise
        except Exception as e:
            logger.error(f"Cell version deletion error: {e}")
            return self._error_response(500, "Failed to delete cell version")
    
    async def handle_search(self, request):
        """Handle cell search request."""
        try:
            # Parse query parameters
            query = request.query.get('q', '')
            limit = int(request.query.get('limit', 20))
            offset = int(request.query.get('offset', 0))
            
            # Search cells
            results, total_count = await self.repository.search_cells(
                query=query,
                limit=limit,
                offset=offset
            )
            
            return web.json_response({
                "query": query,
                "results": results,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            })
            
        except Exception as e:
            logger.error(f"Cell search error: {e}")
            return self._error_response(500, "Search failed")
    
    async def handle_list_capabilities(self, request):
        """Handle capability listing request."""
        try:
            # List capabilities
            capabilities = await self.repository.list_capabilities()
            
            return web.json_response({
                "capabilities": capabilities
            })
            
        except Exception as e:
            logger.error(f"Capability listing error: {e}")
            return self._error_response(500, "Failed to list capabilities")
    
    async def handle_status(self, request):
        """Handle repository status request."""
        try:
            # Get repository status
            status = await self.repository.get_status()
            
            return web.json_response(status)
            
        except Exception as e:
            logger.error(f"Status error: {e}")
            return self._error_response(500, "Failed to get repository status")
    
    async def handle_rebuild_index(self, request):
        """Handle index rebuild request."""
        try:
            # Verify authorization
            token = self._get_auth_token(request)
            if not token:
                raise AuthenticationError("Authentication required")
                
            has_permission = await self.auth_manager.check_permission(token, "admin")
            if not has_permission:
                raise AuthorizationError("Admin privileges required to rebuild index")
                
            # Rebuild index
            success = await self.repository.rebuild_index()
            
            return web.json_response({
                "success": success,
                "message": "Index rebuild initiated" if success else "Index rebuild failed"
            })
            
        except (AuthenticationError, AuthorizationError) as e:
            raise
        except Exception as e:
            logger.error(f"Index rebuild error: {e}")
            return self._error_response(500, "Failed to rebuild index")
    
    def _get_auth_token(self, request) -> Optional[str]:
        """
        Extract authentication token from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Token string or None if not found
        """
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        return None
    
    def _error_response(self, status: int, message: str) -> web.Response:
        """
        Create an error response.
        
        Args:
            status: HTTP status code
            message: Error message
            
        Returns:
            JSON response with error details
        """
        return web.json_response(
            {
                "error": {
                    "status": status,
                    "message": message
                }
            },
            status=status
        )
    
    async def start(self):
        """Start the API server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"Repository API started on http://{self.host}:{self.port}")
        return runner, site
    
    @classmethod
    async def create_and_start(cls, repository: CellRepository, auth_manager: AuthManager, host: str = "localhost", port: int = 8080):
        """
        Create and start the API server.
        
        Args:
            repository: Cell repository instance
            auth_manager: Authentication manager
            host: Host to bind the API server
            port: Port to bind the API server
            
        Returns:
            Tuple of (api_instance, runner, site)
        """
        api = cls(repository, auth_manager, host, port)
        runner, site = await api.start()
        return api, runner, site

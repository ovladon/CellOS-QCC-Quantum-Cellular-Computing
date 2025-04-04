"""
Cell Execution Module for QCC Assembler.

This module provides functionality for executing cells within the QCC architecture.
It manages the cell execution environment, handles inter-cell communication, and
enforces resource constraints and security policies.

Key responsibilities:
- Initialize and execute cells in isolated environments
- Manage cell lifecycle (activation, suspension, resumption, termination)
- Facilitate communication between cells
- Monitor and enforce resource usage limits
- Provide security isolation between cells
"""

import asyncio
import logging
import time
import uuid
import os
import sys
import json
import importlib
import inspect
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable
from datetime import datetime

# Local imports
from qcc.common.exceptions import (
    CellExecutionError, CellNotFoundError, CellCommunicationError,
    ResourceLimitExceededError, SecurityError, CellLifecycleError
)
from qcc.common.models import Cell
import qcc.common.utils as utils

logger = logging.getLogger(__name__)

class CellExecutor:
    """
    Cell Executor manages the execution of cells within the QCC system.
    
    This class is responsible for initializing cells, executing their capabilities,
    managing their lifecycle, and facilitating communication between them.
    It also enforces resource constraints and security policies.
    """
    
    def __init__(self, config: Dict[str, Any], security_manager=None):
        """
        Initialize the Cell Executor.
        
        Args:
            config: Configuration dictionary with execution settings
            security_manager: Security manager for verifying and securing cells
        """
        self.config = config
        self.security_manager = security_manager
        
        # Extract configuration
        self.execution_settings = utils.safe_dict_get(config, 'cells.runtime', {})
        self.execution_timeout_ms = self.execution_settings.get('execution_timeout_ms', 10000)
        self.max_memory_per_cell_mb = self.execution_settings.get('max_memory_per_cell_mb', 100)
        self.max_concurrent_cells = self.execution_settings.get('max_concurrent_cells', 20)
        self.resource_monitoring_interval_ms = self.execution_settings.get('resource_monitoring_interval_ms', 1000)
        
        # Active cells dictionary: cell_id -> cell_instance
        self.active_cells = {}
        
        # Cell resource usage tracking: cell_id -> resource_stats
        self.cell_resources = {}
        
        # Cell communication channels: (source_cell_id, target_cell_id) -> channel
        self.communication_channels = {}
        
        # Resource monitoring task
        self.monitoring_task = None
        
        # Cell execution environments
        self.cell_environments = {}
        
        # Cell capability cache: cell_id -> {capability_name -> function}
        self.capability_cache = {}
        
        logger.info(f"Cell Executor initialized with max {self.max_concurrent_cells} concurrent cells")

    async def start(self):
        """Start the cell executor and resource monitoring."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitor_resources())
            logger.info("Cell resource monitoring started")

    async def stop(self):
        """Stop the cell executor and release all cells."""
        # Cancel resource monitoring
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        # Release all active cells
        cell_ids = list(self.active_cells.keys())
        for cell_id in cell_ids:
            try:
                await self.release_cell(cell_id)
            except Exception as e:
                logger.error(f"Error releasing cell {cell_id} during shutdown: {e}")
        
        logger.info("Cell Executor stopped")

    async def initialize_cell(self, cell: Cell) -> str:
        """
        Initialize a cell for execution.
        
        Args:
            cell: Cell object containing cell metadata and code
            
        Returns:
            Cell ID for the initialized cell
            
        Raises:
            CellExecutionError: If cell initialization fails
            ResourceLimitExceededError: If resource limits would be exceeded
        """
        # Check if we're at the maximum concurrent cells limit
        if len(self.active_cells) >= self.max_concurrent_cells:
            raise ResourceLimitExceededError(f"Maximum concurrent cells limit ({self.max_concurrent_cells}) reached")
        
        # Generate a unique cell ID if not provided
        cell_id = cell.id if hasattr(cell, 'id') and cell.id else str(uuid.uuid4())
        
        try:
            # Create execution environment for the cell
            cell_env = await self._create_cell_environment(cell)
            
            # Store the environment
            self.cell_environments[cell_id] = cell_env
            
            # Initialize cell instance
            cell_instance = await self._instantiate_cell(cell_id, cell, cell_env)
            
            # Store cell instance
            self.active_cells[cell_id] = cell_instance
            
            # Initialize resource tracking
            self.cell_resources[cell_id] = {
                'memory_mb': 0,
                'cpu_percent': 0,
                'start_time': time.time(),
                'last_active': time.time(),
                'capabilities_executed': 0,
                'status': 'initialized'
            }
            
            logger.info(f"Initialized cell {cell_id} of type {getattr(cell, 'cell_type', 'unknown')}")
            
            return cell_id
            
        except Exception as e:
            logger.error(f"Failed to initialize cell: {e}")
            # Clean up any resources
            if cell_id in self.cell_environments:
                await self._destroy_cell_environment(cell_id)
                del self.cell_environments[cell_id]
            
            raise CellExecutionError(f"Cell initialization failed: {str(e)}")

    async def _create_cell_environment(self, cell: Cell) -> Dict[str, Any]:
        """
        Create an execution environment for a cell.
        
        Args:
            cell: Cell object to create environment for
            
        Returns:
            Environment dictionary with execution context
            
        Raises:
            SecurityError: If cell verification fails
        """
        # Security verification if security manager is available
        if self.security_manager:
            verified = await self.security_manager.verify_cell(cell)
            if not verified:
                raise SecurityError(f"Cell verification failed for {cell.id}")
        
        # Create basic environment
        cell_env = {
            'modules': {},
            'globals': {},
            'allowed_imports': self._get_allowed_imports(cell),
            'resource_limits': {
                'memory_mb': self.max_memory_per_cell_mb,
                'execution_timeout_ms': self.execution_timeout_ms
            },
            'security_context': {
                'cell_id': cell.id if hasattr(cell, 'id') else str(uuid.uuid4()),
                'provider': cell.provider if hasattr(cell, 'provider') else 'unknown',
                'permissions': []
            }
        }
        
        # Add cell-specific resource limits if provided
        if hasattr(cell, 'resource_limits') and cell.resource_limits:
            cell_env['resource_limits'].update(cell.resource_limits)
        
        # Setup permission context based on cell type
        if hasattr(cell, 'cell_type'):
            if cell.cell_type == 'system':
                cell_env['security_context']['permissions'].extend([
                    'system:resource_access',
                    'system:file_access',
                    'system:network_access'
                ])
            elif cell.cell_type == 'middleware':
                cell_env['security_context']['permissions'].extend([
                    'middleware:data_processing',
                    'middleware:service_integration'
                ])
        
        return cell_env

    async def _destroy_cell_environment(self, cell_id: str) -> None:
        """
        Destroy a cell's execution environment and clean up resources.
        
        Args:
            cell_id: ID of the cell to clean up
        """
        if cell_id in self.cell_environments:
            # Clean up modules
            for module_name in self.cell_environments[cell_id].get('modules', {}):
                if module_name in sys.modules:
                    try:
                        del sys.modules[module_name]
                    except Exception:
                        pass
            
            # Clean up globals
            self.cell_environments[cell_id]['globals'].clear()
            
            # Remove from environments dictionary
            del self.cell_environments[cell_id]
            
            logger.debug(f"Destroyed environment for cell {cell_id}")

    async def _instantiate_cell(self, cell_id: str, cell: Cell, cell_env: Dict[str, Any]) -> Any:
        """
        Instantiate a cell object from its code or module.
        
        Args:
            cell_id: Unique identifier for the cell
            cell: Cell object containing code or module reference
            cell_env: Execution environment for the cell
            
        Returns:
            Instantiated cell object
            
        Raises:
            CellExecutionError: If cell instantiation fails
        """
        cell_instance = None
        
        try:
            # Different instantiation methods based on cell type
            if hasattr(cell, 'module_path') and cell.module_path:
                # Import from module path
                module_name = cell.module_path
                if module_name in sys.modules:
                    # Reload the module if it's already loaded
                    module = importlib.reload(sys.modules[module_name])
                else:
                    # Import the module
                    module = importlib.import_module(module_name)
                
                # Find the cell class in the module
                cell_class = None
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, object) and obj.__module__ == module_name:
                        if hasattr(obj, 'initialize') and callable(getattr(obj, 'initialize')):
                            cell_class = obj
                            break
                
                if not cell_class:
                    raise CellExecutionError(f"No valid cell class found in module {module_name}")
                
                # Instantiate the cell class
                cell_instance = cell_class()
                
                # Store the module in the environment
                cell_env['modules'][module_name] = module
                
            elif hasattr(cell, 'code') and cell.code:
                # Dynamically execute cell code
                cell_code = cell.code
                
                # Create a namespace for the cell code
                cell_globals = {}
                cell_env['globals'] = cell_globals
                
                # Execute cell code in the namespace
                exec(cell_code, cell_globals)
                
                # Find the cell class in the namespace
                cell_class = None
                for name, obj in cell_globals.items():
                    if inspect.isclass(obj) and hasattr(obj, 'initialize') and callable(getattr(obj, 'initialize')):
                        cell_class = obj
                        break
                
                if not cell_class:
                    raise CellExecutionError("No valid cell class found in cell code")
                
                # Instantiate the cell class
                cell_instance = cell_class()
                
            elif hasattr(cell, 'wasm_module') and cell.wasm_module:
                # For WebAssembly cells, we'd use a WebAssembly runtime
                # This is a simplified placeholder; in a real implementation,
                # we would use a proper WebAssembly runtime like Wasmer or WASM3
                raise CellExecutionError("WebAssembly cells not yet implemented")
            
            else:
                raise CellExecutionError("No valid cell code or module provided")
            
            # Initialize the cell with parameters
            init_params = {
                'cell_id': cell_id,
                'quantum_signature': getattr(cell, 'quantum_signature', None),
                'context': getattr(cell, 'context', {}),
                'configuration': getattr(cell, 'configuration', {})
            }
            
            # Add provider information if available
            if hasattr(cell, 'provider'):
                init_params['provider'] = cell.provider
                
            # Call initialize method
            init_result = await self._execute_cell_method(cell_instance, 'initialize', init_params)
            
            # Validate initialization result
            if not init_result or not isinstance(init_result, dict) or init_result.get('status') != 'success':
                error_msg = "Cell initialization failed"
                if isinstance(init_result, dict) and 'error' in init_result:
                    error_msg = f"Cell initialization failed: {init_result['error']}"
                raise CellExecutionError(error_msg)
            
            # Cache capabilities
            if 'capabilities' in init_result:
                self.capability_cache[cell_id] = {}
                for capability in init_result['capabilities']:
                    capability_name = capability.get('name')
                    if capability_name:
                        # Look for a method with the same name as the capability
                        if hasattr(cell_instance, capability_name) and callable(getattr(cell_instance, capability_name)):
                            self.capability_cache[cell_id][capability_name] = getattr(cell_instance, capability_name)
            
            return cell_instance
            
        except Exception as e:
            logger.error(f"Error instantiating cell {cell_id}: {e}")
            logger.error(traceback.format_exc())
            raise CellExecutionError(f"Cell instantiation failed: {str(e)}")

    def _get_allowed_imports(self, cell: Cell) -> List[str]:
        """
        Determine allowed imports for a cell based on its type and permissions.
        
        Args:
            cell: Cell object
            
        Returns:
            List of allowed module import patterns
        """
        # Base allowed imports for all cells
        allowed_imports = [
            'qcc.common.*',
            'qcc.cells.BaseCell',
            'typing',
            'datetime',
            'json',
            'math',
            'time',
            'uuid'
        ]
        
        # Cell type specific imports
        if hasattr(cell, 'cell_type'):
            if cell.cell_type == 'system':
                allowed_imports.extend([
                    'os.path',
                    'sys',
                    'io',
                    'asyncio',
                    'socket',
                    'ssl',
                    're'
                ])
            elif cell.cell_type == 'middleware':
                allowed_imports.extend([
                    'asyncio',
                    'hashlib',
                    'base64',
                    're'
                ])
        
        # Add imports from cell's declared dependencies if available
        if hasattr(cell, 'dependencies') and cell.dependencies:
            for dependency in cell.dependencies:
                if isinstance(dependency, str):
                    allowed_imports.append(dependency)
                elif isinstance(dependency, dict) and 'module' in dependency:
                    allowed_imports.append(dependency['module'])
        
        return allowed_imports

    async def activate_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Activate a cell that has been initialized.
        
        Args:
            cell_id: ID of the cell to activate
            
        Returns:
            Activation result
            
        Raises:
            CellNotFoundError: If cell is not found
            CellLifecycleError: If cell is not in the correct state
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        # Check cell state
        if self.cell_resources[cell_id]['status'] != 'initialized':
            raise CellLifecycleError(f"Cell {cell_id} is not in 'initialized' state. Current state: {self.cell_resources[cell_id]['status']}")
        
        try:
            # Call activate method if it exists
            cell_instance = self.active_cells[cell_id]
            
            if hasattr(cell_instance, 'activate') and callable(cell_instance.activate):
                result = await self._execute_cell_method(cell_instance, 'activate')
            else:
                # If no activate method, assume success
                result = {
                    'status': 'success',
                    'state': 'active'
                }
            
            # Update cell status
            self.cell_resources[cell_id]['status'] = 'active'
            self.cell_resources[cell_id]['last_active'] = time.time()
            
            logger.info(f"Activated cell {cell_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error activating cell {cell_id}: {e}")
            raise CellLifecycleError(f"Cell activation failed: {str(e)}")

    async def deactivate_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Deactivate an active cell.
        
        Args:
            cell_id: ID of the cell to deactivate
            
        Returns:
            Deactivation result
            
        Raises:
            CellNotFoundError: If cell is not found
            CellLifecycleError: If cell is not in the correct state
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        # Check cell state
        if self.cell_resources[cell_id]['status'] not in ['active', 'suspended']:
            raise CellLifecycleError(f"Cell {cell_id} cannot be deactivated from '{self.cell_resources[cell_id]['status']}' state")
        
        try:
            # Call deactivate method if it exists
            cell_instance = self.active_cells[cell_id]
            
            if hasattr(cell_instance, 'deactivate') and callable(cell_instance.deactivate):
                result = await self._execute_cell_method(cell_instance, 'deactivate')
            else:
                # If no deactivate method, assume success
                result = {
                    'status': 'success',
                    'state': 'deactivated'
                }
            
            # Update cell status
            self.cell_resources[cell_id]['status'] = 'deactivated'
            self.cell_resources[cell_id]['last_active'] = time.time()
            
            logger.info(f"Deactivated cell {cell_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deactivating cell {cell_id}: {e}")
            raise CellLifecycleError(f"Cell deactivation failed: {str(e)}")

    async def suspend_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Suspend an active cell, preserving its state.
        
        Args:
            cell_id: ID of the cell to suspend
            
        Returns:
            Suspension result with saved state
            
        Raises:
            CellNotFoundError: If cell is not found
            CellLifecycleError: If cell is not in the correct state
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        # Check cell state
        if self.cell_resources[cell_id]['status'] != 'active':
            raise CellLifecycleError(f"Cell {cell_id} cannot be suspended from '{self.cell_resources[cell_id]['status']}' state")
        
        try:
            # Call suspend method if it exists
            cell_instance = self.active_cells[cell_id]
            
            if hasattr(cell_instance, 'suspend') and callable(cell_instance.suspend):
                result = await self._execute_cell_method(cell_instance, 'suspend')
            else:
                # If no suspend method, assume success with empty state
                result = {
                    'status': 'success',
                    'state': 'suspended',
                    'saved_state': {}
                }
            
            # Update cell status
            self.cell_resources[cell_id]['status'] = 'suspended'
            self.cell_resources[cell_id]['last_active'] = time.time()
            
            logger.info(f"Suspended cell {cell_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error suspending cell {cell_id}: {e}")
            raise CellLifecycleError(f"Cell suspension failed: {str(e)}")

    async def resume_cell(self, cell_id: str, saved_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Resume a suspended cell with saved state.
        
        Args:
            cell_id: ID of the cell to resume
            saved_state: Saved state from suspension
            
        Returns:
            Resume result
            
        Raises:
            CellNotFoundError: If cell is not found
            CellLifecycleError: If cell is not in the correct state
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        # Check cell state
        if self.cell_resources[cell_id]['status'] != 'suspended':
            raise CellLifecycleError(f"Cell {cell_id} cannot be resumed from '{self.cell_resources[cell_id]['status']}' state")
        
        try:
            # Call resume method if it exists
            cell_instance = self.active_cells[cell_id]
            
            if hasattr(cell_instance, 'resume') and callable(cell_instance.resume):
                params = {}
                if saved_state:
                    params['saved_state'] = saved_state
                
                result = await self._execute_cell_method(cell_instance, 'resume', params)
            else:
                # If no resume method, assume success
                result = {
                    'status': 'success',
                    'state': 'active'
                }
            
            # Update cell status
            self.cell_resources[cell_id]['status'] = 'active'
            self.cell_resources[cell_id]['last_active'] = time.time()
            
            logger.info(f"Resumed cell {cell_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error resuming cell {cell_id}: {e}")
            raise CellLifecycleError(f"Cell resume failed: {str(e)}")

    async def release_cell(self, cell_id: str) -> Dict[str, Any]:
        """
        Release a cell, cleaning up its resources.
        
        Args:
            cell_id: ID of the cell to release
            
        Returns:
            Release result
            
        Raises:
            CellNotFoundError: If cell is not found
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        try:
            # Call release method if it exists
            cell_instance = self.active_cells[cell_id]
            
            if hasattr(cell_instance, 'release') and callable(cell_instance.release):
                result = await self._execute_cell_method(cell_instance, 'release')
            else:
                # If no release method, assume success
                result = {
                    'status': 'success',
                    'state': 'released'
                }
            
            # Clean up cell resources
            await self._destroy_cell_environment(cell_id)
            
            # Remove from active cells
            del self.active_cells[cell_id]
            
            # Remove from resource tracking
            if cell_id in self.cell_resources:
                del self.cell_resources[cell_id]
            
            # Remove from capability cache
            if cell_id in self.capability_cache:
                del self.capability_cache[cell_id]
            
            # Clean up communication channels
            channels_to_remove = []
            for channel_key in self.communication_channels:
                if cell_id in channel_key:
                    channels_to_remove.append(channel_key)
            
            for channel_key in channels_to_remove:
                del self.communication_channels[channel_key]
            
            logger.info(f"Released cell {cell_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error releasing cell {cell_id}: {e}")
            
            # Even if there's an error, try to clean up resources
            try:
                if cell_id in self.cell_environments:
                    await self._destroy_cell_environment(cell_id)
                
                if cell_id in self.active_cells:
                    del self.active_cells[cell_id]
                
                if cell_id in self.cell_resources:
                    del self.cell_resources[cell_id]
                
                if cell_id in self.capability_cache:
                    del self.capability_cache[cell_id]
                
                # Clean up communication channels
                channels_to_remove = []
                for channel_key in self.communication_channels:
                    if cell_id in channel_key:
                        channels_to_remove.append(channel_key)
                
                for channel_key in channels_to_remove:
                    del self.communication_channels[channel_key]
            except Exception as cleanup_error:
                logger.error(f"Error during cell cleanup: {cleanup_error}")
            
            return {
                'status': 'error',
                'error': f"Cell release failed: {str(e)}",
                'state': 'unknown'
            }

    async def execute_capability(self, cell_id: str, capability: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a capability on a cell.
        
        Args:
            cell_id: ID of the cell
            capability: Name of the capability to execute
            parameters: Parameters for the capability
            
        Returns:
            Capability execution result
            
        Raises:
            CellNotFoundError: If cell is not found
            CellExecutionError: If capability execution fails
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        # Check if cell is active
        if self.cell_resources[cell_id]['status'] != 'active':
            raise CellLifecycleError(f"Cell {cell_id} is not active. Current state: {self.cell_resources[cell_id]['status']}")
        
        # Get cell instance
        cell_instance = self.active_cells[cell_id]
        
        # Use cached capability if available
        capability_fn = None
        if cell_id in self.capability_cache and capability in self.capability_cache[cell_id]:
            capability_fn = self.capability_cache[cell_id][capability]
        elif hasattr(cell_instance, capability) and callable(getattr(cell_instance, capability)):
            capability_fn = getattr(cell_instance, capability)
            # Cache the capability
            if cell_id not in self.capability_cache:
                self.capability_cache[cell_id] = {}
            self.capability_cache[cell_id][capability] = capability_fn
        
        if not capability_fn:
            raise CellExecutionError(f"Capability '{capability}' not found in cell {cell_id}")
        
        try:
            # Execute the capability with parameters
            result = await self._execute_cell_method(cell_instance, capability, parameters or {})
            
            # Update resource tracking
            self.cell_resources[cell_id]['last_active'] = time.time()
            self.cell_resources[cell_id]['capabilities_executed'] += 1
            
            # Log execution
            if result and isinstance(result, dict) and result.get('status') == 'success':
                logger.debug(f"Executed capability '{capability}' on cell {cell_id}")
            else:
                logger.warning(f"Capability '{capability}' execution on cell {cell_id} returned status: {result.get('status', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing capability '{capability}' on cell {cell_id}: {e}")
            logger.error(traceback.format_exc())
            raise CellExecutionError(f"Capability execution failed: {str(e)}")

    async def connect_cells(self, source_id: str, target_id: str) -> Tuple[bool, str]:
        """
        Establish a connection between two cells.
        
        Args:
            source_id: ID of the source cell
            target_id: ID of the target cell
            
        Returns:
            Tuple containing:
            - Success indicator (True/False)
            - Channel ID or error message
            
        Raises:
            CellNotFoundError: If either cell is not found
            CellCommunicationError: If connection fails
        """
        # Check if cells exist
        if source_id not in self.active_cells:
            raise CellNotFoundError(f"Source cell {source_id} not found")
        
        if target_id not in self.active_cells:
            raise CellNotFoundError(f"Target cell {target_id} not found")
        
        # Check if connection already exists
        if (source_id, target_id) in self.communication_channels:
            return True, self.communication_channels[(source_id, target_id)]['id']
        
        try:
            # Create a new channel
            channel_id = f"channel_{source_id[:8]}_{target_id[:8]}_{str(uuid.uuid4())[:8]}"
            
            # Create bidirectional communication queue
            queue_source_to_target = asyncio.Queue()
            queue_target_to_source = asyncio.Queue()
            
            # Store the channel
            self.communication_channels[(source_id, target_id)] = {
                'id': channel_id,
                'created_at': time.time(),
                'queue': queue_source_to_target,
                'source': source_id,
                'target': target_id
            }
            
            self.communication_channels[(target_id, source_id)] = {
                'id': channel_id,
                'created_at': time.time(),
                'queue': queue_target_to_source,
                'source': target_id,
                'target': source_id
            }
            
            # Set up the connection in the cells if they support it
            source_cell = self.active_cells[source_id]
            target_cell = self.active_cells[target_id]
            
            # Add the connection to the source cell
            if hasattr(source_cell, 'add_connection') and callable(source_cell.add_connection):
                await self._execute_cell_method(source_cell, 'add_connection', {
                    'target_id': target_id,
                    'channel_id': channel_id,
                    'direction': 'outgoing'
                })
            
            # Add the connection to the target cell
            if hasattr(target_cell, 'add_connection') and callable(target_cell.add_connection):
                await self._execute_cell_method(target_cell, 'add_connection', {
                    'target_id': source_id,
                    'channel_id': channel_id,
                    'direction': 'incoming'
                })
            
            logger.info(f"Connected cells {source_id} and {target_id} with channel {channel_id}")
            
            return True, channel_id
            
        except Exception as e:
            logger.error(f"Error connecting cells {source_id} and {target_id}: {e}")
            raise CellCommunicationError(f"Failed to connect cells: {str(e)}")

    async def disconnect_cells(self, source_id: str, target_id: str) -> bool:
        """
        Disconnect two previously connected cells.
        
        Args:
            source_id: ID of the source cell
            target_id: ID of the target cell
            
        Returns:
            Success indicator (True/False)
            
        Raises:
            CellNotFoundError: If either cell is not found
            CellCommunicationError: If disconnection fails
        """
        # Check if cells exist
        if source_id not in self.active_cells:
            raise CellNotFoundError(f"Source cell {source_id} not found")
        
        if target_id not in self.active_cells:
            raise CellNotFoundError(f"Target cell {target_id} not found")
        
        # Check if connection exists
        if (source_id, target_id) not in self.communication_channels:
            logger.warning(f"No connection found between cells {source_id} and {target_id}")
            return False
        
        try:
            # Get channel information
            channel_id = self.communication_channels[(source_id, target_id)]['id']
            
            # Notify cells about disconnection
            source_cell = self.active_cells[source_id]
            target_cell = self.active_cells[target_id]
            
            # Notify source cell
            if hasattr(source_cell, 'remove_connection') and callable(source_cell.remove_connection):
                await self._execute_cell_method(source_cell, 'remove_connection', {
                    'target_id': target_id,
                    'channel_id': channel_id
                })
            
            # Notify target cell
            if hasattr(target_cell, 'remove_connection') and callable(target_cell.remove_connection):
                await self._execute_cell_method(target_cell, 'remove_connection', {
                    'target_id': source_id,
                    'channel_id': channel_id
                })
            
            # Remove the channels
            del self.communication_channels[(source_id, target_id)]
            if (target_id, source_id) in self.communication_channels:
                del self.communication_channels[(target_id, source_id)]
            
            logger.info(f"Disconnected cells {source_id} and {target_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting cells {source_id} and {target_id}: {e}")
            raise CellCommunicationError(f"Failed to disconnect cells: {str(e)}")

    async def send_message(self, source_id: str, target_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message from one cell to another.
        
        Args:
            source_id: ID of the source cell
            target_id: ID of the target cell
            message: Message content
            
        Returns:
            Success indicator (True/False)
            
        Raises:
            CellNotFoundError: If either cell is not found
            CellCommunicationError: If message sending fails
        """
        # Check if cells exist
        if source_id not in self.active_cells:
            raise CellNotFoundError(f"Source cell {source_id} not found")
        
        if target_id not in self.active_cells:
            raise CellNotFoundError(f"Target cell {target_id} not found")
        
        # Check if connection exists
        if (source_id, target_id) not in self.communication_channels:
            raise CellCommunicationError(f"No connection between cells {source_id} and {target_id}")
        
        try:
            # Get the communication channel
            channel = self.communication_channels[(source_id, target_id)]
            queue = channel['queue']
            
            # Prepare message with metadata
            message_with_metadata = {
                'source_id': source_id,
                'target_id': target_id,
                'timestamp': time.time(),
                'message_id': str(uuid.uuid4()),
                'content': message
            }
            
            # Put message in queue
            await queue.put(message_with_metadata)
            
            # Update last activity
            self.cell_resources[source_id]['last_active'] = time.time()
            self.cell_resources[target_id]['last_active'] = time.time()
            
            logger.debug(f"Message sent from {source_id} to {target_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message from {source_id} to {target_id}: {e}")
            raise CellCommunicationError(f"Failed to send message: {str(e)}")

    async def receive_message(self, cell_id: str, sender_id: str = None, timeout: float = None) -> Optional[Dict[str, Any]]:
        """
        Receive a message for a cell, optionally from a specific sender.
        
        Args:
            cell_id: ID of the receiving cell
            sender_id: Optional ID of the sending cell
            timeout: Optional timeout in seconds
            
        Returns:
            Message or None if timeout occurs
            
        Raises:
            CellNotFoundError: If cell is not found
            CellCommunicationError: If message receiving fails
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        try:
            # If sender is specified, check for messages from that sender
            if sender_id:
                # Check if connection exists
                if (sender_id, cell_id) not in self.communication_channels:
                    raise CellCommunicationError(f"No connection between cells {sender_id} and {cell_id}")
                
                # Get the communication channel
                channel = self.communication_channels[(sender_id, cell_id)]
                queue = channel['queue']
                
                # Try to get message with timeout
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=timeout)
                    queue.task_done()
                    
                    # Update last activity
                    self.cell_resources[cell_id]['last_active'] = time.time()
                    
                    logger.debug(f"Message received by {cell_id} from {sender_id}")
                    
                    return message
                except asyncio.TimeoutError:
                    return None
            
            else:
                # Check for messages from any connected cell
                # Collect all queues where this cell is the target
                queues = []
                for key, channel in self.communication_channels.items():
                    source, target = key
                    if target == cell_id:
                        queues.append((source, channel['queue']))
                
                if not queues:
                    logger.warning(f"Cell {cell_id} has no incoming connections")
                    return None
                
                # Create tasks to wait on all queues
                tasks = []
                for source_id, queue in queues:
                    task = asyncio.create_task(queue.get())
                    tasks.append((source_id, task, queue))
                
                # Wait for first message or timeout
                done, pending = await asyncio.wait(
                    [task for _, task, _ in tasks],
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel all pending tasks
                for _, task, _ in tasks:
                    if task in pending:
                        task.cancel()
                
                # Get the completed task and mark as done
                if done:
                    # Find which task completed
                    for source_id, task, queue in tasks:
                        if task in done:
                            message = task.result()
                            queue.task_done()
                            
                            # Update last activity
                            self.cell_resources[cell_id]['last_active'] = time.time()
                            
                            logger.debug(f"Message received by {cell_id} from {source_id}")
                            
                            return message
                
                return None
                
        except Exception as e:
            logger.error(f"Error receiving message for {cell_id}: {e}")
            raise CellCommunicationError(f"Failed to receive message: {str(e)}")

    async def call_cell_capability(self, source_id: str, target_id: str, capability: str, 
                                   parameters: Dict[str, Any] = None, timeout: float = None) -> Dict[str, Any]:
        """
        Call a capability on another cell.
        
        Args:
            source_id: ID of the calling cell
            target_id: ID of the target cell
            capability: Name of the capability to call
            parameters: Parameters for the capability
            timeout: Optional timeout in seconds
            
        Returns:
            Capability execution result
            
        Raises:
            CellNotFoundError: If either cell is not found
            CellCommunicationError: If call fails
            CellExecutionError: If capability execution fails
        """
        # Check if cells exist
        if source_id not in self.active_cells:
            raise CellNotFoundError(f"Source cell {source_id} not found")
        
        if target_id not in self.active_cells:
            raise CellNotFoundError(f"Target cell {target_id} not found")
        
        # Check if connection exists or establish one
        if (source_id, target_id) not in self.communication_channels:
            logger.debug(f"No existing connection between {source_id} and {target_id}, establishing one")
            success, _ = await self.connect_cells(source_id, target_id)
            if not success:
                raise CellCommunicationError(f"Failed to establish connection between cells {source_id} and {target_id}")
        
        try:
            # Execute the capability on the target cell
            result = await self.execute_capability(target_id, capability, parameters or {})
            
            # Update last activity
            self.cell_resources[source_id]['last_active'] = time.time()
            self.cell_resources[target_id]['last_active'] = time.time()
            
            logger.debug(f"Cell {source_id} called capability '{capability}' on cell {target_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling capability '{capability}' from {source_id} to {target_id}: {e}")
            raise CellCommunicationError(f"Failed to call capability: {str(e)}")

    async def get_cell_status(self, cell_id: str) -> Dict[str, Any]:
        """
        Get the current status and resource usage of a cell.
        
        Args:
            cell_id: ID of the cell
            
        Returns:
            Dictionary with cell status and resource usage
            
        Raises:
            CellNotFoundError: If cell is not found
        """
        # Check if cell exists
        if cell_id not in self.active_cells:
            raise CellNotFoundError(f"Cell {cell_id} not found")
        
        # Return current status and resource usage
        status = {
            'cell_id': cell_id,
            'status': self.cell_resources[cell_id]['status'],
            'resources': {
                'memory_mb': self.cell_resources[cell_id]['memory_mb'],
                'cpu_percent': self.cell_resources[cell_id]['cpu_percent']
            },
            'uptime_seconds': time.time() - self.cell_resources[cell_id]['start_time'],
            'last_active_seconds': time.time() - self.cell_resources[cell_id]['last_active'],
            'capabilities_executed': self.cell_resources[cell_id]['capabilities_executed']
        }
        
        return status

    async def get_active_cells(self) -> List[Dict[str, Any]]:
        """
        Get a list of all active cells and their status.
        
        Returns:
            List of dictionaries with cell information
        """
        cell_list = []
        
        for cell_id in self.active_cells:
            cell_info = await self.get_cell_status(cell_id)
            cell_list.append(cell_info)
        
        return cell_list

    async def _execute_cell_method(self, cell_instance: Any, method_name: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Execute a method on a cell instance with timeout and resource monitoring.
        
        Args:
            cell_instance: Cell instance
            method_name: Method name to call
            parameters: Optional parameters for the method
            
        Returns:
            Method result
            
        Raises:
            CellExecutionError: If method execution fails
            ResourceLimitExceededError: If execution exceeds resource limits
        """
        if not hasattr(cell_instance, method_name) or not callable(getattr(cell_instance, method_name)):
            raise CellExecutionError(f"Method {method_name} not found or not callable")
        
        method = getattr(cell_instance, method_name)
        
        # Prepare parameters if any
        params = parameters or {}
        
        try:
            # Run with timeout
            timeout_seconds = self.execution_timeout_ms / 1000
            result = await asyncio.wait_for(
                self._call_method_async(method, params),
                timeout=timeout_seconds
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Method {method_name} execution timed out after {timeout_seconds} seconds")
            raise CellExecutionError(f"Method execution timed out after {timeout_seconds} seconds")
        
        except Exception as e:
            logger.error(f"Error executing method {method_name}: {e}")
            raise CellExecutionError(f"Method execution failed: {str(e)}")

    async def _call_method_async(self, method: Callable, params: Dict[str, Any]) -> Any:
        """
        Call a method asynchronously, handling both async and sync methods.
        
        Args:
            method: Method to call
            params: Parameters for the method
            
        Returns:
            Method result
        """
        if inspect.iscoroutinefunction(method):
            # Method is already async
            return await method(**params)
        else:
            # Method is synchronous, run in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: method(**params)
            )

    async def _monitor_resources(self) -> None:
        """Monitor resource usage of all active cells and enforce limits."""
        import psutil
        
        process = psutil.Process()
        
        while True:
            try:
                # Sleep first to allow initialization
                await asyncio.sleep(self.resource_monitoring_interval_ms / 1000)
                
                # Skip if no active cells
                if not self.active_cells:
                    continue
                
                # Get current process memory usage
                process_memory = process.memory_info().rss / (1024 * 1024)  # MB
                
                # Distribute memory usage proportionally among active cells
                # This is a simplified approach; in a real implementation,
                # we would use more sophisticated resource tracking
                per_cell_memory = process_memory / max(len(self.active_cells), 1)
                
                # Update resource usage for all cells
                for cell_id in list(self.active_cells.keys()):
                    # Skip if cell was removed during iteration
                    if cell_id not in self.cell_resources:
                        continue
                    
                    # Update memory usage
                    self.cell_resources[cell_id]['memory_mb'] = per_cell_memory
                    
                    # Check if memory limit exceeded
                    cell_memory_limit = self.cell_environments.get(cell_id, {}).get('resource_limits', {}).get(
                        'memory_mb', self.max_memory_per_cell_mb)
                    
                    if per_cell_memory > cell_memory_limit:
                        logger.warning(f"Cell {cell_id} exceeded memory limit: {per_cell_memory:.2f}MB > {cell_memory_limit}MB")
                        
                        # Handle limit exceeded based on policy
                        enforcement_policy = self.execution_settings.get('resource_limit_policy', 'suspend')
                        
                        if enforcement_policy == 'terminate':
                            logger.error(f"Terminating cell {cell_id} due to memory limit violation")
                            try:
                                await self.release_cell(cell_id)
                            except Exception as e:
                                logger.error(f"Error releasing cell after limit violation: {e}")
                        
                        elif enforcement_policy == 'suspend':
                            logger.warning(f"Suspending cell {cell_id} due to memory limit violation")
                            try:
                                if self.cell_resources[cell_id]['status'] == 'active':
                                    await self.suspend_cell(cell_id)
                            except Exception as e:
                                logger.error(f"Error suspending cell after limit violation: {e}")
                
            except asyncio.CancelledError:
                # Task was cancelled, exit gracefully
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                # Continue monitoring despite errors
                await asyncio.sleep(self.resource_monitoring_interval_ms / 1000)
        
        logger.info("Resource monitoring stopped")

# Cell factory function for the assembler
def create_cell_executor(config: Dict[str, Any], security_manager=None) -> CellExecutor:
    """
    Create and initialize a cell executor.
    
    Args:
        config: Configuration dictionary
        security_manager: Optional security manager
        
    Returns:
        Initialized CellExecutor instance
    """
    executor = CellExecutor(config, security_manager)
    
    # Return the executor without starting it
    # The caller is responsible for starting it
    return executor

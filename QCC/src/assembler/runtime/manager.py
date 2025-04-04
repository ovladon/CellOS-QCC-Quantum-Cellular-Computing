"""
Runtime Manager for QCC Assembler.

This module provides high-level runtime management for the QCC Assembler,
coordinating multiple cell solutions, managing resources, and interfacing
between the assembler core and the cell executor.

Key responsibilities:
- Manage the lifecycle of solutions (collections of cells)
- Coordinate resource allocation across multiple solutions
- Facilitate solution-level operations (activation, suspension, resumption)
- Interface with the cell executor for low-level cell operations
- Handle communication setup between cells within a solution
- Monitor solution-level performance metrics
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from datetime import datetime

# Local imports
from qcc.assembler.runtime.executor import CellExecutor, create_cell_executor
from qcc.common.exceptions import (
    SolutionNotFoundError, SolutionLifecycleError,
    ResourceLimitExceededError, SecurityError
)
from qcc.common.models import Solution, Cell
from qcc.common.utils import safe_dict_get

logger = logging.getLogger(__name__)

class RuntimeManager:
    """
    Runtime Manager for the QCC Assembler.
    
    This class serves as a coordination layer between the assembler and the cell executor,
    managing multiple solutions, handling resource allocation, and providing a higher-level
    interface for solution management.
    """
    
    def __init__(self, config: Dict[str, Any], security_manager=None):
        """
        Initialize the Runtime Manager.
        
        Args:
            config: Configuration dictionary with runtime settings
            security_manager: Security manager for cell verification
        """
        self.config = config
        self.security_manager = security_manager
        
        # Extract runtime settings
        self.runtime_settings = safe_dict_get(config, 'cells.runtime', {})
        
        # Initialize the cell executor
        self.cell_executor = create_cell_executor(config, security_manager)
        
        # Active solutions dictionary: solution_id -> solution_data
        self.active_solutions = {}
        
        # Solution to cell mapping: solution_id -> set(cell_ids)
        self.solution_cells = {}
        
        # Resource allocation tracking
        self.resource_allocations = {
            'total_memory_mb': 0,
            'total_cpu_percent': 0,
            'solutions_count': 0
        }
        
        # Resource limits
        self.max_solutions = safe_dict_get(self.runtime_settings, 'max_concurrent_solutions', 50)
        self.max_total_memory_mb = safe_dict_get(self.runtime_settings, 'max_total_memory_mb', 2048)
        self.max_total_cpu_percent = safe_dict_get(self.runtime_settings, 'max_total_cpu_percent', 90)
        
        # Performance monitoring
        self.monitoring_enabled = safe_dict_get(self.runtime_settings, 'monitoring_enabled', True)
        self.monitoring_interval_sec = safe_dict_get(self.runtime_settings, 'monitoring_interval_sec', 60)
        self.monitoring_task = None
        
        logger.info(f"Runtime Manager initialized with max {self.max_solutions} concurrent solutions")

    async def start(self):
        """Start the runtime manager and all its components."""
        logger.info("Starting Runtime Manager")
        
        # Start the cell executor
        await self.cell_executor.start()
        
        # Start performance monitoring if enabled
        if self.monitoring_enabled and self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitor_performance())
            logger.info("Solution performance monitoring started")

    async def stop(self):
        """Stop the runtime manager and release all resources."""
        logger.info("Stopping Runtime Manager")
        
        # Cancel performance monitoring
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        # Release all active solutions
        solution_ids = list(self.active_solutions.keys())
        for solution_id in solution_ids:
            try:
                await self.release_solution(solution_id)
            except Exception as e:
                logger.error(f"Error releasing solution {solution_id} during shutdown: {e}")
        
        # Stop the cell executor
        await self.cell_executor.stop()
        
        logger.info("Runtime Manager stopped")

    async def assemble_solution(self, solution: Solution, cells: Dict[str, Cell]) -> Solution:
        """
        Assemble a solution by initializing and connecting its cells.
        
        Args:
            solution: Solution object with metadata
            cells: Dictionary of cells to include in the solution
            
        Returns:
            Updated Solution object with initialized cells
            
        Raises:
            ResourceLimitExceededError: If resource limits would be exceeded
            SecurityError: If cell verification fails
        """
        logger.info(f"Assembling solution {solution.id} with {len(cells)} cells")
        
        # Check if we're at the maximum concurrent solutions limit
        if len(self.active_solutions) >= self.max_solutions:
            raise ResourceLimitExceededError(f"Maximum concurrent solutions limit ({self.max_solutions}) reached")
        
        # Reserve solution ID
        if solution.id in self.active_solutions:
            logger.warning(f"Solution ID {solution.id} already exists, generating new ID")
            solution.id = str(uuid.uuid4())
        
        # Initialize cells and track them
        initialized_cells = {}
        solution_cell_ids = set()
        
        try:
            # Initialize each cell
            for cell_id, cell in cells.items():
                # Initialize cell
                cell_runtime_id = await self.cell_executor.initialize_cell(cell)
                
                # Store mapping of original ID to runtime ID if different
                if cell_id != cell_runtime_id:
                    logger.debug(f"Cell ID mapping: {cell_id} -> {cell_runtime_id}")
                
                # Add to tracking
                initialized_cells[cell_runtime_id] = cell
                solution_cell_ids.add(cell_runtime_id)
            
            # Store solution to cell mapping
            self.solution_cells[solution.id] = solution_cell_ids
            
            # Establish connections between cells based on solution's connection map
            connection_map = getattr(solution, 'connection_map', {})
            for source_id, targets in connection_map.items():
                for target_id in targets:
                    # Check if both cells are in this solution
                    if source_id in solution_cell_ids and target_id in solution_cell_ids:
                        await self.cell_executor.connect_cells(source_id, target_id)
                    else:
                        logger.warning(f"Cannot connect cells {source_id} -> {target_id}: one or both cells not in solution")
            
            # Store solution data
            self.active_solutions[solution.id] = {
                'solution': solution,
                'created_at': datetime.now().isoformat(),
                'status': 'assembled',
                'cells': initialized_cells,
                'resource_usage': {
                    'memory_mb': 0,
                    'cpu_percent': 0
                },
                'metrics': {
                    'cell_count': len(initialized_cells),
                    'activation_time_ms': 0,
                    'execution_count': 0
                }
            }
            
            # Update resource allocations
            self.resource_allocations['solutions_count'] += 1
            
            # Update the solution object with cell data
            solution.cells = initialized_cells
            solution.status = 'assembled'
            
            logger.info(f"Solution {solution.id} assembled successfully with {len(initialized_cells)} cells")
            
            return solution
            
        except Exception as e:
            logger.error(f"Error assembling solution {solution.id}: {e}")
            
            # Clean up any initialized cells
            for cell_id in solution_cell_ids:
                try:
                    await self.cell_executor.release_cell(cell_id)
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up cell {cell_id} after assembly failure: {cleanup_error}")
            
            # Remove solution tracking if it was added
            if solution.id in self.solution_cells:
                del self.solution_cells[solution.id]
            
            raise

    async def activate_solution(self, solution_id: str) -> Solution:
        """
        Activate all cells in a solution, transitioning it to active state.
        
        Args:
            solution_id: ID of the solution to activate
            
        Returns:
            Updated Solution object
            
        Raises:
            SolutionNotFoundError: If solution is not found
            SolutionLifecycleError: If solution is not in the correct state
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        # Check if solution is in the correct state
        if solution_data['status'] != 'assembled':
            if solution_data['status'] == 'active':
                logger.warning(f"Solution {solution_id} is already active")
                return solution_data['solution']
            else:
                raise SolutionLifecycleError(f"Solution {solution_id} cannot be activated from '{solution_data['status']}' state")
        
        logger.info(f"Activating solution {solution_id} with {len(solution_data['cells'])} cells")
        
        start_time = time.time()
        
        try:
            # Activate each cell
            for cell_id in self.solution_cells[solution_id]:
                await self.cell_executor.activate_cell(cell_id)
            
            # Update solution status
            solution_data['status'] = 'active'
            solution_data['activated_at'] = datetime.now().isoformat()
            
            # Update solution object
            solution_data['solution'].status = 'active'
            
            # Record activation time
            activation_time_ms = int((time.time() - start_time) * 1000)
            solution_data['metrics']['activation_time_ms'] = activation_time_ms
            
            logger.info(f"Solution {solution_id} activated in {activation_time_ms}ms")
            
            return solution_data['solution']
            
        except Exception as e:
            logger.error(f"Error activating solution {solution_id}: {e}")
            
            # Update solution status to error
            solution_data['status'] = 'error'
            solution_data['solution'].status = 'error'
            
            raise SolutionLifecycleError(f"Solution activation failed: {str(e)}")

    async def suspend_solution(self, solution_id: str) -> Solution:
        """
        Suspend all cells in a solution, preserving their state.
        
        Args:
            solution_id: ID of the solution to suspend
            
        Returns:
            Updated Solution object with saved state
            
        Raises:
            SolutionNotFoundError: If solution is not found
            SolutionLifecycleError: If solution is not in the correct state
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        # Check if solution is in the correct state
        if solution_data['status'] != 'active':
            raise SolutionLifecycleError(f"Solution {solution_id} cannot be suspended from '{solution_data['status']}' state")
        
        logger.info(f"Suspending solution {solution_id}")
        
        try:
            # Suspend each cell and collect state
            saved_states = {}
            
            for cell_id in self.solution_cells[solution_id]:
                result = await self.cell_executor.suspend_cell(cell_id)
                
                # Store saved state if returned
                if isinstance(result, dict) and 'saved_state' in result:
                    saved_states[cell_id] = result['saved_state']
            
            # Update solution status
            solution_data['status'] = 'suspended'
            solution_data['suspended_at'] = datetime.now().isoformat()
            solution_data['saved_states'] = saved_states
            
            # Update solution object
            solution_data['solution'].status = 'suspended'
            
            logger.info(f"Solution {solution_id} suspended with {len(saved_states)} cell states saved")
            
            return solution_data['solution']
            
        except Exception as e:
            logger.error(f"Error suspending solution {solution_id}: {e}")
            
            # Don't update status to error, leave as active
            
            raise SolutionLifecycleError(f"Solution suspension failed: {str(e)}")

    async def resume_solution(self, solution_id: str) -> Solution:
        """
        Resume a suspended solution, restoring cell states.
        
        Args:
            solution_id: ID of the solution to resume
            
        Returns:
            Updated Solution object
            
        Raises:
            SolutionNotFoundError: If solution is not found
            SolutionLifecycleError: If solution is not in the correct state
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        # Check if solution is in the correct state
        if solution_data['status'] != 'suspended':
            if solution_data['status'] == 'active':
                logger.warning(f"Solution {solution_id} is already active")
                return solution_data['solution']
            else:
                raise SolutionLifecycleError(f"Solution {solution_id} cannot be resumed from '{solution_data['status']}' state")
        
        logger.info(f"Resuming solution {solution_id}")
        
        try:
            # Resume each cell with its saved state
            saved_states = solution_data.get('saved_states', {})
            
            for cell_id in self.solution_cells[solution_id]:
                saved_state = saved_states.get(cell_id)
                await self.cell_executor.resume_cell(cell_id, saved_state)
            
            # Update solution status
            solution_data['status'] = 'active'
            solution_data['resumed_at'] = datetime.now().isoformat()
            
            # Update solution object
            solution_data['solution'].status = 'active'
            
            logger.info(f"Solution {solution_id} resumed successfully")
            
            return solution_data['solution']
            
        except Exception as e:
            logger.error(f"Error resuming solution {solution_id}: {e}")
            
            # Update solution status to error
            solution_data['status'] = 'error'
            solution_data['solution'].status = 'error'
            
            raise SolutionLifecycleError(f"Solution resumption failed: {str(e)}")

    async def release_solution(self, solution_id: str) -> bool:
        """
        Release a solution, cleaning up all its cells and resources.
        
        Args:
            solution_id: ID of the solution to release
            
        Returns:
            Success indicator (True/False)
            
        Raises:
            SolutionNotFoundError: If solution is not found
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        logger.info(f"Releasing solution {solution_id}")
        
        try:
            # Get cell IDs for this solution
            cell_ids = list(self.solution_cells.get(solution_id, set()))
            
            # Release each cell
            errors = []
            for cell_id in cell_ids:
                try:
                    await self.cell_executor.release_cell(cell_id)
                except Exception as e:
                    logger.error(f"Error releasing cell {cell_id}: {e}")
                    errors.append(str(e))
            
            # Clean up solution resources
            if solution_id in self.solution_cells:
                del self.solution_cells[solution_id]
            
            if solution_id in self.active_solutions:
                del self.active_solutions[solution_id]
            
            # Update resource allocations
            self.resource_allocations['solutions_count'] -= 1
            
            logger.info(f"Solution {solution_id} released with {len(errors)} errors")
            
            return len(errors) == 0
            
        except Exception as e:
            logger.error(f"Error during solution release: {e}")
            
            # Attempt to clean up tracking even if there's an error
            if solution_id in self.solution_cells:
                del self.solution_cells[solution_id]
            
            if solution_id in self.active_solutions:
                del self.active_solutions[solution_id]
            
            self.resource_allocations['solutions_count'] -= 1
            
            return False

    async def execute_cell_capability(self, solution_id: str, cell_id: str, capability: str,
                                     parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a capability on a cell within a solution.
        
        Args:
            solution_id: ID of the solution
            cell_id: ID of the cell
            capability: Name of the capability to execute
            parameters: Parameters for the capability
            
        Returns:
            Capability execution result
            
        Raises:
            SolutionNotFoundError: If solution is not found
            SolutionLifecycleError: If solution is not active
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        # Check if solution is active
        if solution_data['status'] != 'active':
            raise SolutionLifecycleError(f"Solution {solution_id} is not active (current state: {solution_data['status']})")
        
        # Check if cell is part of this solution
        if cell_id not in self.solution_cells[solution_id]:
            raise SolutionLifecycleError(f"Cell {cell_id} is not part of solution {solution_id}")
        
        try:
            # Execute the capability
            result = await self.cell_executor.execute_capability(cell_id, capability, parameters)
            
            # Update metrics
            solution_data['metrics']['execution_count'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing capability {capability} on cell {cell_id} in solution {solution_id}: {e}")
            raise

    async def call_between_cells(self, solution_id: str, source_cell_id: str, target_cell_id: str,
                                capability: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call a capability on a target cell from a source cell within the same solution.
        
        Args:
            solution_id: ID of the solution
            source_cell_id: ID of the calling cell
            target_cell_id: ID of the target cell
            capability: Name of the capability to call
            parameters: Parameters for the capability
            
        Returns:
            Capability execution result
            
        Raises:
            SolutionNotFoundError: If solution is not found
            SolutionLifecycleError: If solution is not active or cells not in solution
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        # Check if solution is active
        if solution_data['status'] != 'active':
            raise SolutionLifecycleError(f"Solution {solution_id} is not active (current state: {solution_data['status']})")
        
        # Check if cells are part of this solution
        solution_cells = self.solution_cells[solution_id]
        if source_cell_id not in solution_cells:
            raise SolutionLifecycleError(f"Source cell {source_cell_id} is not part of solution {solution_id}")
        
        if target_cell_id not in solution_cells:
            raise SolutionLifecycleError(f"Target cell {target_cell_id} is not part of solution {solution_id}")
        
        try:
            # Call the capability
            result = await self.cell_executor.call_cell_capability(
                source_cell_id, target_cell_id, capability, parameters)
            
            # Update metrics
            solution_data['metrics']['execution_count'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error in cell-to-cell call from {source_cell_id} to {target_cell_id} in solution {solution_id}: {e}")
            raise

    async def get_solution_status(self, solution_id: str) -> Dict[str, Any]:
        """
        Get the current status and resource usage of a solution.
        
        Args:
            solution_id: ID of the solution
            
        Returns:
            Dictionary with solution status and resource usage
            
        Raises:
            SolutionNotFoundError: If solution is not found
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise SolutionNotFoundError(f"Solution {solution_id} not found")
        
        solution_data = self.active_solutions[solution_id]
        
        # Get current resource usage for all cells in the solution
        total_memory = 0
        total_cpu = 0
        cell_statuses = []
        
        for cell_id in self.solution_cells[solution_id]:
            try:
                cell_status = await self.cell_executor.get_cell_status(cell_id)
                cell_statuses.append(cell_status)
                
                # Accumulate resource usage
                total_memory += cell_status['resources']['memory_mb']
                total_cpu += cell_status['resources']['cpu_percent']
            except Exception as e:
                logger.error(f"Error getting status for cell {cell_id}: {e}")
                cell_statuses.append({
                    'cell_id': cell_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Update solution resource usage
        solution_data['resource_usage'] = {
            'memory_mb': total_memory,
            'cpu_percent': total_cpu
        }
        
        # Calculate duration
        created_at = datetime.fromisoformat(solution_data['created_at'])
        duration_seconds = (datetime.now() - created_at).total_seconds()
        
        # Prepare status response
        status = {
            'solution_id': solution_id,
            'status': solution_data['status'],
            'created_at': solution_data['created_at'],
            'duration_seconds': duration_seconds,
            'cell_count': len(self.solution_cells[solution_id]),
            'resources': solution_data['resource_usage'],
            'metrics': solution_data['metrics'],
            'cells': cell_statuses
        }
        
        # Add state transition timestamps if they exist
        for time_field in ['activated_at', 'suspended_at', 'resumed_at']:
            if time_field in solution_data:
                status[time_field] = solution_data[time_field]
        
        return status

    async def get_active_solutions(self) -> List[Dict[str, Any]]:
        """
        Get a list of all active solutions and their status.
        
        Returns:
            List of dictionaries with solution information
        """
        solution_list = []
        
        for solution_id in self.active_solutions:
            try:
                solution_info = await self.get_solution_status(solution_id)
                solution_list.append(solution_info)
            except Exception as e:
                logger.error(f"Error getting status for solution {solution_id}: {e}")
                solution_list.append({
                    'solution_id': solution_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        return solution_list

    async def get_system_resources(self) -> Dict[str, Any]:
        """
        Get current system-wide resource usage and limits.
        
        Returns:
            Dictionary with resource information
        """
        # Collect current resource usage from all solutions
        total_memory = 0
        total_cpu = 0
        
        for solution_id, solution_data in self.active_solutions.items():
            total_memory += solution_data['resource_usage'].get('memory_mb', 0)
            total_cpu += solution_data['resource_usage'].get('cpu_percent', 0)
        
        # Update global resource tracking
        self.resource_allocations['total_memory_mb'] = total_memory
        self.resource_allocations['total_cpu_percent'] = total_cpu
        
        # Prepare resource information
        resources = {
            'usage': {
                'memory_mb': total_memory,
                'cpu_percent': total_cpu,
                'solutions_count': len(self.active_solutions)
            },
            'limits': {
                'max_memory_mb': self.max_total_memory_mb,
                'max_cpu_percent': self.max_total_cpu_percent,
                'max_solutions': self.max_solutions
            },
            'utilization': {
                'memory_percent': (total_memory / self.max_total_memory_mb * 100) if self.max_total_memory_mb > 0 else 0,
                'cpu_percent': (total_cpu / self.max_total_cpu_percent * 100) if self.max_total_cpu_percent > 0 else 0,
                'solutions_percent': (len(self.active_solutions) / self.max_solutions * 100) if self.max_solutions > 0 else 0
            }
        }
        
        return resources

    async def _monitor_performance(self) -> None:
        """Periodically monitor solution performance and resource usage."""
        while True:
            try:
                # Sleep first to allow initialization
                await asyncio.sleep(self.monitoring_interval_sec)
                
                # Skip if no active solutions
                if not self.active_solutions:
                    continue
                
                # Update resource usage for all solutions
                await self._update_resource_usage()
                
                # Log system-wide resource usage
                resources = await self.get_system_resources()
                logger.info(f"System resources: {len(self.active_solutions)} solutions, "
                           f"{resources['usage']['memory_mb']:.1f}MB memory, "
                           f"{resources['usage']['cpu_percent']:.1f}% CPU")
                
            except asyncio.CancelledError:
                # Task was cancelled, exit gracefully
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                # Continue monitoring despite errors
                await asyncio.sleep(self.monitoring_interval_sec)
        
        logger.info("Performance monitoring stopped")

    async def _update_resource_usage(self) -> None:
        """Update resource usage for all active solutions."""
        for solution_id in list(self.active_solutions.keys()):
            # Skip if solution was removed
            if solution_id not in self.active_solutions:
                continue
            
            try:
                # Get current resource usage for all cells in the solution
                total_memory = 0
                total_cpu = 0
                
                for cell_id in self.solution_cells.get(solution_id, set()):
                    try:
                        cell_status = await self.cell_executor.get_cell_status(cell_id)
                        
                        # Accumulate resource usage
                        total_memory += cell_status['resources']['memory_mb']
                        total_cpu += cell_status['resources']['cpu_percent']
                    except Exception as e:
                        logger.error(f"Error getting status for cell {cell_id}: {e}")
                
                # Update solution resource usage
                self.active_solutions[solution_id]['resource_usage'] = {
                    'memory_mb': total_memory,
                    'cpu_percent': total_cpu
                }
                
            except Exception as e:
                logger.error(f"Error updating resource usage for solution {solution_id}: {e}")

# Runtime manager factory function for the assembler
def create_runtime_manager(config: Dict[str, Any], security_manager=None) -> RuntimeManager:
    """
    Create and initialize a runtime manager.
    
    Args:
        config: Configuration dictionary
        security_manager: Optional security manager
        
    Returns:
        Initialized RuntimeManager instance
    """
    manager = RuntimeManager(config, security_manager)
    
    # Return the manager without starting it
    # The caller is responsible for starting it
    return manager

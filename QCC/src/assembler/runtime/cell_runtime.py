"""
Cell Runtime implementation for the QCC Assembler.

This module provides the CellRuntime class, which manages the
execution environment for cells in the QCC system.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set

from qcc.common.models import Cell

from .cell_connector import CellConnector
from .lifecycle_manager import LifecycleManager
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)

class CellRuntime:
    """
    Manages the execution environment for cells.
    
    The CellRuntime handles cell lifecycle management, resource
    allocation, and inter-cell communication.
    
    Attributes:
        connector (CellConnector): Handles connections between cells
        lifecycle_manager (LifecycleManager): Manages cell lifecycle states
        resource_manager (ResourceManager): Manages resource allocation
        active_cells (Dict[str, Cell]): Currently active cells
    """
    
    def __init__(self):
        """Initialize the cell runtime."""
        self.connector = CellConnector()
        self.lifecycle_manager = LifecycleManager()
        self.resource_manager = ResourceManager()
        self.active_cells = {}
        
        logger.info("Cell runtime initialized")
        
    async def activate_cell(self, cell: Cell) -> bool:
        """
        Activate a cell for execution.
        
        Args:
            cell: Cell to activate
            
        Returns:
            Success indicator
            
        Raises:
            RuntimeError: If activation fails
        """
        logger.info(f"Activating cell: {cell.id}")
        
        # Allocate resources
        resources_allocated = await self.resource_manager.allocate_resources(cell)
        if not resources_allocated:
            logger.error(f"Failed to allocate resources for cell: {cell.id}")
            raise RuntimeError(f"Resource allocation failed for cell: {cell.id}")
            
        # Activate the cell
        activated = await self.lifecycle_manager.activate(cell)
        if not activated:
            # Release resources if activation fails
            await self.resource_manager.release_resources(cell)
            logger.error(f"Failed to activate cell: {cell.id}")
            raise RuntimeError(f"Activation failed for cell: {cell.id}")
            
        # Add to active cells
        self.active_cells[cell.id] = cell
        logger.info(f"Cell activated: {cell.id}")
        
        return True
        
    async def deactivate_cell(self, cell: Cell) -> bool:
        """
        Deactivate a cell.
        
        Args:
            cell: Cell to deactivate
            
        Returns:
            Success indicator
        """
        logger.info(f"Deactivating cell: {cell.id}")
        
        # Deactivate the cell
        deactivated = await self.lifecycle_manager.deactivate(cell)
        
        # Release resources
        await self.resource_manager.release_resources(cell)
        
        # Remove from active cells
        if cell.id in self.active_cells:
            del self.active_cells[cell.id]
            
        logger.info(f"Cell deactivated: {cell.id}")
        return deactivated
        
    async def suspend_cell(self, cell: Cell) -> Dict[str, Any]:
        """
        Suspend a cell, preserving its state.
        
        Args:
            cell: Cell to suspend
            
        Returns:
            Cell state for later resumption
        """
        logger.info(f"Suspending cell: {cell.id}")
        
        # Suspend the cell
        state = await self.lifecycle_manager.suspend(cell)
        
        # Partially release resources
        await self.resource_manager.reduce_resources(cell)
        
        logger.info(f"Cell suspended: {cell.id}")
        return state
        
    async def resume_cell(self, cell: Cell, state: Dict[str, Any]) -> bool:
        """
        Resume a suspended cell.
        
        Args:
            cell: Cell to resume
            state: Cell state from suspension
            
        Returns:
            Success indicator
        """
        logger.info(f"Resuming cell: {cell.id}")
        
        # Reallocate resources
        resources_allocated = await self.resource_manager.allocate_resources(cell)
        if not resources_allocated:
            logger.error(f"Failed to allocate resources for resuming cell: {cell.id}")
            return False
            
        # Resume the cell
        resumed = await self.lifecycle_manager.resume(cell, state)
        
        logger.info(f"Cell resumed: {cell.id}")
        return resumed
        
    async def release_cell(self, cell: Cell) -> bool:
        """
        Release a cell completely.
        
        Args:
            cell: Cell to release
            
        Returns:
            Success indicator
        """
        logger.info(f"Releasing cell: {cell.id}")
        
        # Deactivate if active
        if cell.id in self.active_cells:
            await self.deactivate_cell(cell)
            
        # Release the cell
        released = await self.lifecycle_manager.release(cell)
        
        # Ensure resources are released
        await self.resource_manager.release_resources(cell)
        
        logger.info(f"Cell released: {cell.id}")
        return released
        
    async def connect_cells(self, source_cell: Cell, target_cell: Cell) -> bool:
        """
        Establish a connection between cells.
        
        Args:
            source_cell: Source cell for the connection
            target_cell: Target cell for the connection
            
        Returns:
            Success indicator
        """
        logger.info(f"Connecting cells: {source_cell.id} -> {target_cell.id}")
        
        # Create the connection
        connected = await self.connector.connect(source_cell, target_cell)
        
        logger.info(f"Cells connected: {source_cell.id} -> {target_cell.id}")
        return connected
        
    async def disconnect_cells(self, source_cell: Cell, target_cell: Cell) -> bool:
        """
        Remove a connection between cells.
        
        Args:
            source_cell: Source cell for the connection
            target_cell: Target cell for the connection
            
        Returns:
            Success indicator
        """
        logger.info(f"Disconnecting cells: {source_cell.id} -> {target_cell.id}")
        
        # Remove the connection
        disconnected = await self.connector.disconnect(source_cell, target_cell)
        
        logger.info(f"Cells disconnected: {source_cell.id} -> {target_cell.id}")
        return disconnected
        
    async def execute_capability(
        self, 
        cell: Cell, 
        capability: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a capability on a cell.
        
        Args:
            cell: Cell to execute on
            capability: Capability to execute
            parameters: Parameters for the capability
            
        Returns:
            Result of the capability execution
        """
        logger.info(f"Executing capability on cell {cell.id}: {capability}")
        parameters = parameters or {}
        
        # Check if cell is active
        if cell.id not in self.active_cells:
            logger.error(f"Cannot execute capability on inactive cell: {cell.id}")
            return {
                "status": "error",
                "error": f"Cell {cell.id} is not active"
            }
            
        # Execute the capability
        try:
            result = await self.lifecycle_manager.execute_capability(cell, capability, parameters)
            
            # Update resource usage metrics
            if "performance_metrics" in result:
                await self.resource_manager.update_usage_metrics(cell, result["performance_metrics"])
                
            logger.info(f"Capability executed: {capability} on {cell.id}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing capability {capability} on cell {cell.id}: {e}")
            return {
                "status": "error",
                "error": f"Error executing capability: {str(e)}"
            }
        
    async def get_cell_status(self, cell: Cell) -> Dict[str, Any]:
        """
        Get the current status of a cell.
        
        Args:
            cell: Cell to get status for
            
        Returns:
            Dictionary with cell status information
        """
        logger.debug(f"Getting status for cell: {cell.id}")
        
        # Get cell lifecycle status
        lifecycle_status = await self.lifecycle_manager.get_status(cell)
        
        # Get resource usage
        resource_usage = await self.resource_manager.get_usage(cell)
        
        # Combine information
        status = {
            "id": cell.id,
            "status": lifecycle_status["status"],
            "active": cell.id in self.active_cells,
            "resource_usage": resource_usage,
            "connections": await self.connector.get_connections(cell)
        }
        
        logger.debug(f"Cell status retrieved: {cell.id}")
        return status

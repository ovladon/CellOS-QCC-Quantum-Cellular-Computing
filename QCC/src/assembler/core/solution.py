"""
Solution model for the QCC Assembler.

This module defines the Solution class, which represents an assembled
set of cells working together to fulfill a user intent.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class Solution:
    """
    Represents an assembled solution of cells.
    
    A solution consists of a set of interconnected cells that together
    fulfill a specific user intent.
    
    Attributes:
        id (str): Unique identifier for this solution
        cells (Dict[str, Cell]): Cells that make up this solution
        quantum_signature (str): Quantum-resistant signature for security
        created_at (str): ISO timestamp of when the solution was created
        intent (Dict[str, Any]): Analyzed user intent
        status (str): Current status of the solution (active, suspended, error)
        context (Dict[str, Any]): Context in which the solution was created
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        cells: Optional[Dict[str, Any]] = None,
        quantum_signature: Optional[str] = None,
        created_at: Optional[str] = None,
        intent: Optional[Dict[str, Any]] = None,
        status: str = "initializing",
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a solution.
        
        Args:
            id: Unique identifier (generated if not provided)
            cells: Dictionary of cells keyed by cell ID
            quantum_signature: Security signature
            created_at: Creation timestamp (current time if not provided)
            intent: Analyzed user intent
            status: Initial status
            context: Solution context
        """
        self.id = id or str(uuid.uuid4())
        self.cells = cells or {}
        self.quantum_signature = quantum_signature
        self.created_at = created_at or datetime.now().isoformat()
        self.intent = intent or {}
        self.status = status
        self.context = context or {}
        
        # Performance metrics
        self.memory_peak_mb = 0
        self.cpu_usage_avg = 0
        
    def add_cell(self, cell_id: str, cell: Any) -> None:
        """
        Add a cell to the solution.
        
        Args:
            cell_id: Unique identifier for the cell
            cell: Cell object
        """
        self.cells[cell_id] = cell
        
    def remove_cell(self, cell_id: str) -> bool:
        """
        Remove a cell from the solution.
        
        Args:
            cell_id: ID of the cell to remove
            
        Returns:
            True if the cell was removed, False if it wasn't in the solution
        """
        if cell_id in self.cells:
            del self.cells[cell_id]
            return True
        return False
    
    def get_cell(self, cell_id: str) -> Optional[Any]:
        """
        Get a cell by ID.
        
        Args:
            cell_id: ID of the cell to retrieve
            
        Returns:
            Cell object or None if not found
        """
        return self.cells.get(cell_id)
    
    def get_cells_by_capability(self, capability: str) -> List[Any]:
        """
        Get all cells with a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of cells with the specified capability
        """
        return [
            cell for cell in self.cells.values()
            if hasattr(cell, 'capability') and cell.capability == capability
        ]
    
    def update_status(self, new_status: str) -> None:
        """
        Update the solution status.
        
        Args:
            new_status: New status string
        """
        self.status = new_status
        
    def update_metrics(self, memory_mb: float, cpu_percent: float) -> None:
        """
        Update performance metrics.
        
        Args:
            memory_mb: Current memory usage in MB
            cpu_percent: Current CPU usage percentage
        """
        # Update peak memory
        self.memory_peak_mb = max(self.memory_peak_mb, memory_mb)
        
        # Update average CPU usage (simple running average)
        if not hasattr(self, '_cpu_samples'):
            self._cpu_samples = 0
            self.cpu_usage_avg = 0
            
        self._cpu_samples += 1
        self.cpu_usage_avg = (self.cpu_usage_avg * (self._cpu_samples - 1) + cpu_percent) / self._cpu_samples
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the solution to a dictionary representation.
        
        Returns:
            Dictionary representation of the solution
        """
        # Convert cells to dictionary format for serialization
        cells_dict = {}
        for cell_id, cell in self.cells.items():
            if hasattr(cell, 'to_dict'):
                cells_dict[cell_id] = cell.to_dict()
            else:
                cells_dict[cell_id] = {"id": cell_id}
        
        return {
            "id": self.id,
            "cells": cells_dict,
            "quantum_signature": self.quantum_signature,
            "created_at": self.created_at,
            "intent": self.intent,
            "status": self.status,
            "context": self.context,
            "memory_peak_mb": self.memory_peak_mb,
            "cpu_usage_avg": self.cpu_usage_avg
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Solution':
        """
        Create a solution from a dictionary representation.
        
        Args:
            data: Dictionary representation of a solution
            
        Returns:
            Solution object
        """
        solution = cls(
            id=data.get("id"),
            cells=data.get("cells", {}),
            quantum_signature=data.get("quantum_signature"),
            created_at=data.get("created_at"),
            intent=data.get("intent", {}),
            status=data.get("status", "initializing"),
            context=data.get("context", {})
        )
        
        # Set metrics
        solution.memory_peak_mb = data.get("memory_peak_mb", 0)
        solution.cpu_usage_avg = data.get("cpu_usage_avg", 0)
        
        return solution

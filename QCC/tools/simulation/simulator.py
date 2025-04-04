"""
QCC Simulation Environment

This module provides a simulation environment for testing and evaluating
the Quantum Cellular Computing system in controlled scenarios without
requiring a full deployment.

The simulator allows:
- Creating virtual cells with simulated capabilities
- Testing the assembler with controlled inputs
- Running predefined scenarios to evaluate behavior
- Recording and replaying interactions for debugging
- Measuring performance metrics in controlled conditions
"""

import asyncio
import logging
import json
import os
import time
import uuid
import random
import argparse
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from datetime import datetime
import yaml
import shutil
import copy
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("qcc.simulator")

class SimulatedCell:
    """
    Represents a simulated cell with configurable behavior.
    
    Simulated cells mimic the behavior of real cells without requiring
    actual implementation. They respond to the same API but with 
    predetermined responses.
    
    Attributes:
        id (str): Unique identifier for this cell
        cell_type (str): Type of cell being simulated
        capability (str): Primary capability of the cell
        version (str): Version of the cell
        status (str): Current status of the cell
        behaviors (Dict): Configured behaviors for cell methods
        latency (Dict): Configured latencies for cell operations
        resource_usage (Dict): Simulated resource consumption
        error_rate (float): Probability of introducing errors
    """
    
    def __init__(
        self,
        cell_type: str,
        capability: str,
        version: str = "1.0.0",
        behaviors: Dict[str, Any] = None,
        latency: Dict[str, float] = None,
        resource_usage: Dict[str, float] = None,
        error_rate: float = 0.0
    ):
        """
        Initialize a simulated cell.
        
        Args:
            cell_type: Type of cell to simulate
            capability: Primary capability to expose
            version: Version to report
            behaviors: Dictionary of method behaviors
            latency: Dictionary of method latencies (in seconds)
            resource_usage: Dictionary of resource consumption
            error_rate: Probability of errors (0.0 to 1.0)
        """
        self.id = str(uuid.uuid4())
        self.cell_type = cell_type
        self.capability = capability
        self.version = version
        self.status = "initialized"
        self.behaviors = behaviors or {}
        self.latency = latency or {
            "initialize": 0.1,
            "configure": 0.05,
            "activate": 0.2,
            "deactivate": 0.1,
            "suspend": 0.1,
            "resume": 0.1,
            "release": 0.05,
            "execute_capability": 0.2
        }
        self.resource_usage = resource_usage or {
            "memory_mb": 50,
            "cpu_percent": 5,
            "storage_mb": 10
        }
        self.error_rate = error_rate
        
        # Cell state
        self.parameters = {}
        self.connections = []
        self.events = []
        self.execution_count = 0
        self.created_at = datetime.now().isoformat()
        
        # Detailed state for more complex simulations
        self._state = {
            "memory_usage": 0,  # Current memory usage
            "data": {},         # Stored data
            "settings": {},     # Configuration settings
            "errors": []        # List of encountered errors
        }
        
        logger.debug(f"Created simulated cell {self.id} of type {cell_type}")
    
    async def initialize(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize the simulated cell.
        
        Args:
            parameters: Initialization parameters
            
        Returns:
            Initialization result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("initialize", 0.1))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "cell_id": self.id,
                "error": {
                    "code": "CELL_INIT_ERROR",
                    "message": "Simulated error during initialization"
                }
            }
        
        # Store parameters
        self.parameters = parameters
        self.quantum_signature = parameters.get("quantum_signature", "")
        self.context = parameters.get("context", {})
        
        # Update status
        self.status = "initialized"
        
        # Use custom behavior if defined
        if "initialize" in self.behaviors:
            if callable(self.behaviors["initialize"]):
                result = self.behaviors["initialize"](parameters)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["initialize"]
        
        # Default behavior
        capabilities = [{
            "name": self.capability,
            "version": self.version,
            "parameters": [
                {
                    "name": "input",
                    "type": "string",
                    "required": True
                }
            ],
            "outputs": [
                {
                    "name": "result",
                    "type": "string"
                }
            ]
        }]
        
        # Add any additional capabilities from behaviors
        if "capabilities" in self.behaviors:
            if isinstance(self.behaviors["capabilities"], list):
                capabilities.extend(self.behaviors["capabilities"])
        
        return {
            "status": "success",
            "cell_id": self.id,
            "capabilities": capabilities,
            "required_connections": self.behaviors.get("required_connections", []),
            "resource_usage": {
                "memory_mb": self.resource_usage.get("memory_mb", 50),
                "storage_mb": self.resource_usage.get("storage_mb", 10)
            }
        }
    
    async def configure(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Configure the simulated cell.
        
        Args:
            parameters: Configuration parameters
            
        Returns:
            Configuration result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("configure", 0.05))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_CONFIG_ERROR",
                    "message": "Simulated error during configuration"
                }
            }
        
        # Update cell state
        if "configuration" in parameters:
            self._state["settings"].update(parameters["configuration"])
        
        # Use custom behavior if defined
        if "configure" in self.behaviors:
            if callable(self.behaviors["configure"]):
                result = self.behaviors["configure"](parameters)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["configure"]
        
        # Default behavior
        return {
            "status": "success",
            "applied_configuration": parameters.get("configuration", {})
        }
    
    async def activate(self) -> Dict[str, Any]:
        """
        Activate the simulated cell.
        
        Returns:
            Activation result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("activate", 0.2))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_ACTIVATION_ERROR",
                    "message": "Simulated error during activation"
                }
            }
        
        # Update status
        self.status = "active"
        
        # Use custom behavior if defined
        if "activate" in self.behaviors:
            if callable(self.behaviors["activate"]):
                result = self.behaviors["activate"]()
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["activate"]
        
        # Default behavior
        return {
            "status": "success",
            "state": "active"
        }
    
    async def deactivate(self) -> Dict[str, Any]:
        """
        Deactivate the simulated cell.
        
        Returns:
            Deactivation result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("deactivate", 0.1))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_DEACTIVATION_ERROR",
                    "message": "Simulated error during deactivation"
                }
            }
        
        # Update status
        self.status = "deactivated"
        
        # Use custom behavior if defined
        if "deactivate" in self.behaviors:
            if callable(self.behaviors["deactivate"]):
                result = self.behaviors["deactivate"]()
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["deactivate"]
        
        # Default behavior
        return {
            "status": "success",
            "state": "deactivated"
        }
    
    async def suspend(self) -> Dict[str, Any]:
        """
        Suspend the simulated cell.
        
        Returns:
            Suspension result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("suspend", 0.1))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_SUSPENSION_ERROR",
                    "message": "Simulated error during suspension"
                }
            }
        
        # Update status
        self.status = "suspended"
        
        # Use custom behavior if defined
        if "suspend" in self.behaviors:
            if callable(self.behaviors["suspend"]):
                result = self.behaviors["suspend"]()
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["suspend"]
        
        # Default behavior
        return {
            "status": "success",
            "state": "suspended",
            "memory_snapshot_id": f"snapshot-{uuid.uuid4()}"
        }
    
    async def resume(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume the simulated cell.
        
        Args:
            parameters: Resume parameters
            
        Returns:
            Resume result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("resume", 0.1))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_RESUME_ERROR",
                    "message": "Simulated error during resumption"
                }
            }
        
        # Update status
        self.status = "active"
        
        # Use custom behavior if defined
        if "resume" in self.behaviors:
            if callable(self.behaviors["resume"]):
                result = self.behaviors["resume"](parameters)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["resume"]
        
        # Default behavior
        return {
            "status": "success",
            "state": "active"
        }
    
    async def release(self) -> Dict[str, Any]:
        """
        Release the simulated cell.
        
        Returns:
            Release result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("release", 0.05))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_RELEASE_ERROR",
                    "message": "Simulated error during release"
                }
            }
        
        # Update status
        self.status = "released"
        
        # Use custom behavior if defined
        if "release" in self.behaviors:
            if callable(self.behaviors["release"]):
                result = self.behaviors["release"]()
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["release"]
        
        # Default behavior
        return {
            "status": "success",
            "state": "released"
        }
    
    async def connect_to(self, target_cell_id: str, interface_name: str = None) -> Dict[str, Any]:
        """
        Connect this cell to another cell.
        
        Args:
            target_cell_id: ID of the cell to connect to
            interface_name: Name of the interface to connect to
            
        Returns:
            Connection result
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("connect", 0.05))
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "error": {
                    "code": "CELL_CONNECTION_ERROR",
                    "message": "Simulated error during connection"
                }
            }
        
        # Record connection
        connection_id = str(uuid.uuid4())
        self.connections.append({
            "connection_id": connection_id,
            "target_cell_id": target_cell_id,
            "interface_name": interface_name,
            "status": "active",
            "created_at": datetime.now().isoformat()
        })
        
        # Use custom behavior if defined
        if "connect_to" in self.behaviors:
            if callable(self.behaviors["connect_to"]):
                result = self.behaviors["connect_to"](target_cell_id, interface_name)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["connect_to"]
        
        # Default behavior
        return {
            "status": "success",
            "connection_id": connection_id,
            "interface": {
                "name": interface_name or "default",
                "type": "message"
            }
        }
    
    async def execute_capability(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a capability of the simulated cell.
        
        Args:
            parameters: Capability execution parameters
            
        Returns:
            Capability execution result
        """
        # Apply latency
        capability = parameters.get("capability", self.capability)
        latency_key = f"execute_{capability}"
        default_latency = self.latency.get("execute_capability", 0.2)
        await asyncio.sleep(self.latency.get(latency_key, default_latency))
        
        # Increment execution count
        self.execution_count += 1
        
        # Check for random error
        if random.random() < self.error_rate:
            return {
                "status": "error",
                "outputs": [{
                    "name": "error",
                    "value": f"Simulated error during capability execution ({capability})",
                    "type": "string"
                }],
                "performance_metrics": {
                    "execution_time_ms": int(default_latency * 1000),
                    "memory_used_mb": self.resource_usage.get("memory_mb", 50) / 2
                }
            }
        
        # Use custom behavior if defined
        custom_key = f"execute_{capability}"
        if custom_key in self.behaviors:
            if callable(self.behaviors[custom_key]):
                result = self.behaviors[custom_key](parameters)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors[custom_key]
        
        if "execute_capability" in self.behaviors:
            if callable(self.behaviors["execute_capability"]):
                result = self.behaviors["execute_capability"](parameters)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            else:
                return self.behaviors["execute_capability"]
        
        # Default behavior - echo input as output
        input_value = "No input provided"
        if "parameters" in parameters:
            input_value = str(parameters["parameters"].get("input", input_value))
        
        return {
            "status": "success",
            "outputs": [{
                "name": "result",
                "value": f"Simulated {capability} result for input: {input_value}",
                "type": "string"
            }],
            "performance_metrics": {
                "execution_time_ms": int(default_latency * 1000),
                "memory_used_mb": self.resource_usage.get("memory_mb", 50) / 2
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the simulated cell to a dictionary representation.
        
        Returns:
            Dictionary representation of the cell
        """
        return {
            "id": self.id,
            "cell_type": self.cell_type,
            "capability": self.capability,
            "version": self.version,
            "status": self.status,
            "created_at": self.created_at,
            "resource_usage": self.resource_usage,
            "execution_count": self.execution_count,
            "connections": self.connections
        }


class SimulatedProvider:
    """
    Simulates a cell provider service.
    
    The simulated provider maintains a repository of simulated cells and
    provides them on request based on capability or specific cell type.
    
    Attributes:
        id (str): Unique identifier for this provider
        name (str): Provider name
        cells (Dict): Dictionary of available cell templates
        served_requests (int): Count of served requests
        latency (Dict): Configured latencies for provider operations
        error_rate (float): Probability of introducing errors
    """
    
    def __init__(
        self,
        name: str = "simulated_provider",
        cells: Dict[str, Dict[str, Any]] = None,
        latency: Dict[str, float] = None,
        error_rate: float = 0.0
    ):
        """
        Initialize a simulated provider.
        
        Args:
            name: Provider name
            cells: Dictionary of cell templates
            latency: Dictionary of operation latencies
            error_rate: Probability of errors (0.0 to 1.0)
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.cells = cells or {}
        self.served_requests = 0
        self.latency = latency or {
            "get_cell": 0.2,
            "get_cell_for_capability": 0.3
        }
        self.error_rate = error_rate
        
        # Create default cells if none provided
        if not self.cells:
            self._create_default_cells()
        
        logger.debug(f"Created simulated provider {self.id} with {len(self.cells)} cell templates")
    
    def _create_default_cells(self):
        """Create a set of default cell templates."""
        default_cells = {
            "file_system": {
                "cell_type": "file_system",
                "capability": "file_system",
                "version": "1.0.0",
                "resource_usage": {
                    "memory_mb": 30,
                    "cpu_percent": 2,
                    "storage_mb": 100
                }
            },
            "text_generation": {
                "cell_type": "text_generation",
                "capability": "text_generation",
                "version": "1.0.0",
                "resource_usage": {
                    "memory_mb": 200,
                    "cpu_percent": 30,
                    "storage_mb": 50
                }
            },
            "ui_rendering": {
                "cell_type": "ui_rendering",
                "capability": "ui_rendering",
                "version": "1.0.0",
                "resource_usage": {
                    "memory_mb": 80,
                    "cpu_percent": 15,
                    "storage_mb": 20
                }
            },
            "data_visualization": {
                "cell_type": "data_visualization",
                "capability": "data_visualization",
                "version": "1.0.0",
                "resource_usage": {
                    "memory_mb": 100,
                    "cpu_percent": 20,
                    "storage_mb": 30
                }
            },
            "network_interface": {
                "cell_type": "network_interface",
                "capability": "network_interface",
                "version": "1.0.0",
                "resource_usage": {
                    "memory_mb": 40,
                    "cpu_percent": 5,
                    "storage_mb": 15
                }
            }
        }
        
        self.cells.update(default_cells)
    
    async def get_capabilities(self) -> Dict[str, List[str]]:
        """
        Get the list of capabilities provided by this provider.
        
        Returns:
            Dictionary mapping capabilities to cell types
        """
        # Build capabilities map
        capabilities = {}
        for cell_id, cell_info in self.cells.items():
            capability = cell_info.get("capability")
            cell_type = cell_info.get("cell_type")
            
            if capability not in capabilities:
                capabilities[capability] = []
            
            if cell_type not in capabilities[capability]:
                capabilities[capability].append(cell_type)
        
        return capabilities
    
    async def get_cell(
        self,
        cell_type: str,
        version: str = "latest",
        quantum_signature: str = None,
        parameters: Dict[str, Any] = None
    ) -> SimulatedCell:
        """
        Get a cell by type and version.
        
        Args:
            cell_type: Type of cell to retrieve
            version: Version of the cell (default: "latest")
            quantum_signature: Quantum signature for security
            parameters: Additional parameters
            
        Returns:
            SimulatedCell instance
            
        Raises:
            Exception: If the cell is not found or an error occurs
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("get_cell", 0.2))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception(f"Simulated error retrieving cell {cell_type}")
        
        # Check if cell type exists
        if cell_type not in self.cells:
            raise Exception(f"Cell type not found: {cell_type}")
        
        # Get cell template
        cell_template = self.cells[cell_type]
        
        # Create simulated cell
        cell = SimulatedCell(
            cell_type=cell_template.get("cell_type", cell_type),
            capability=cell_template.get("capability", cell_type),
            version=cell_template.get("version", version),
            behaviors=cell_template.get("behaviors", {}),
            latency=cell_template.get("latency", {}),
            resource_usage=cell_template.get("resource_usage", {}),
            error_rate=cell_template.get("error_rate", self.error_rate)
        )
        
        self.served_requests += 1
        logger.debug(f"Provider {self.id} created cell {cell.id} of type {cell_type}")
        
        return cell
    
    async def get_cell_for_capability(
        self,
        capability: str,
        quantum_signature: str = None,
        parameters: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> SimulatedCell:
        """
        Get a cell for a specific capability.
        
        Args:
            capability: Required capability
            quantum_signature: Quantum signature for security
            parameters: Additional parameters
            context: Context information
            
        Returns:
            SimulatedCell instance
            
        Raises:
            Exception: If no cell with the capability is found or an error occurs
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("get_cell_for_capability", 0.3))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception(f"Simulated error retrieving cell for capability {capability}")
        
        # Find cells with the requested capability
        matching_cells = []
        for cell_id, cell_info in self.cells.items():
            if cell_info.get("capability") == capability:
                matching_cells.append(cell_id)
        
        if not matching_cells:
            raise Exception(f"No cells found for capability: {capability}")
        
        # Select a cell (in a real system, this would use more sophisticated selection)
        selected_cell = random.choice(matching_cells)
        
        # Get the selected cell
        cell = await self.get_cell(
            cell_type=selected_cell,
            quantum_signature=quantum_signature,
            parameters=parameters
        )
        
        logger.debug(f"Provider {self.id} selected cell {cell.id} for capability {capability}")
        
        return cell
    
    def add_cell_template(
        self,
        cell_type: str,
        capability: str,
        version: str = "1.0.0",
        behaviors: Dict[str, Any] = None,
        resource_usage: Dict[str, float] = None,
        error_rate: float = None
    ) -> None:
        """
        Add a new cell template to the provider.
        
        Args:
            cell_type: Type of cell
            capability: Capability provided by the cell
            version: Cell version
            behaviors: Dictionary of method behaviors
            resource_usage: Dictionary of resource consumption
            error_rate: Probability of errors
        """
        self.cells[cell_type] = {
            "cell_type": cell_type,
            "capability": capability,
            "version": version,
            "behaviors": behaviors or {},
            "resource_usage": resource_usage or {
                "memory_mb": 50,
                "cpu_percent": 5,
                "storage_mb": 10
            },
            "error_rate": error_rate if error_rate is not None else self.error_rate
        }
        
        logger.debug(f"Added cell template {cell_type} with capability {capability}")


class SimulatedQuantumTrail:
    """
    Simulates the quantum trail system.
    
    The simulated quantum trail maintains a record of cell assemblies
    and usage patterns, similar to the real quantum trail but with
    simplified behavior.
    
    Attributes:
        id (str): Unique identifier for this quantum trail instance
        trail_data (Dict): Dictionary of recorded trails
        patterns (Dict): Dictionary of recognized patterns
        latency (Dict): Configured latencies for operations
        error_rate (float): Probability of introducing errors
    """
    
    def __init__(
        self,
        latency: Dict[str, float] = None,
        error_rate: float = 0.0
    ):
        """
        Initialize a simulated quantum trail.
        
        Args:
            latency: Dictionary of operation latencies
            error_rate: Probability of errors (0.0 to 1.0)
        """
        self.id = str(uuid.uuid4())
        self.trail_data = {}
        self.patterns = {}
        self.latency = latency or {
            "generate_signature": 0.1,
            "record_assembly": 0.2,
            "find_similar_configurations": 0.3
        }
        self.error_rate = error_rate
        
        logger.debug(f"Created simulated quantum trail {self.id}")
    
    async def generate_signature(
        self,
        user_id: str,
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a quantum-resistant signature.
        
        Args:
            user_id: Anonymous user identifier
            intent: User intent information
            context: Context information
            
        Returns:
            Quantum signature string
            
        Raises:
            Exception: If an error occurs during signature generation
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("generate_signature", 0.1))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception("Simulated error generating quantum signature")
        
        # Generate a deterministic but unique signature
        base = f"{user_id}:{time.time()}"
        signature = f"qsig-{uuid.uuid5(uuid.NAMESPACE_DNS, base)}"
        
        logger.debug(f"Generated quantum signature {signature}")
        
        return signature
    
    async def record_assembly(
        self,
        quantum_signature: str,
        solution_id: str,
        cell_ids: List[str],
        connection_map: Dict[str, List[str]],
        performance_metrics: Dict[str, Any] = None
    ) -> bool:
        """
        Record a cell assembly in the quantum trail.
        
        Args:
            quantum_signature: Quantum signature for the assembly
            solution_id: Unique identifier for the solution
            cell_ids: List of cell IDs in the assembly
            connection_map: Map of connections between cells
            performance_metrics: Performance metrics for the assembly
            
        Returns:
            Success indicator
            
        Raises:
            Exception: If an error occurs during recording
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("record_assembly", 0.2))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception(f"Simulated error recording assembly {solution_id}")
        
        # Record assembly data
        self.trail_data[quantum_signature] = {
            "quantum_signature": quantum_signature,
            "solution_id": solution_id,
            "cell_ids": cell_ids,
            "connection_map": connection_map,
            "performance_metrics": performance_metrics or {},
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Update patterns (simplified pattern recognition)
        cell_count = len(cell_ids)
        cell_set = frozenset(cell_ids)
        
        if cell_count not in self.patterns:
            self.patterns[cell_count] = {}
        
        if cell_set not in self.patterns[cell_count]:
            self.patterns[cell_count][cell_set] = []
        
        self.patterns[cell_count][cell_set].append(quantum_signature)
        
        logger.debug(f"Recorded assembly {solution_id} with signature {quantum_signature}")
        
        return True
    
    async def update_assembly_record(
        self,
        quantum_signature: str,
        solution_id: str,
        status: str,
        performance_metrics: Dict[str, Any] = None
    ) -> bool:
        """
        Update an existing assembly record.
        
        Args:
            quantum_signature: Quantum signature for the assembly
            solution_id: Unique identifier for the solution
            status: New status of the assembly
            performance_metrics: Updated performance metrics
            
        Returns:
            Success indicator
            
        Raises:
            Exception: If the record is not found or an error occurs
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("update_assembly_record", 0.1))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception(f"Simulated error updating assembly record {solution_id}")
        
        # Check if record exists
        if quantum_signature not in self.trail_data:
            raise Exception(f"Assembly record not found: {quantum_signature}")
        
        # Update record
        self.trail_data[quantum_signature]["status"] = status
        
        if performance_metrics:
            self.trail_data[quantum_signature]["performance_metrics"].update(performance_metrics)
        
        self.trail_data[quantum_signature]["updated_at"] = datetime.now().isoformat()
        
        logger.debug(f"Updated assembly record {solution_id} to status {status}")
        
        return True
    
    async def find_similar_configurations(
        self,
        capabilities: List[str],
        context_similarity: Dict[str, Any] = None,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find similar configurations based on capabilities and context.
        
        Args:
            capabilities: List of required capabilities
            context_similarity: Context information for similarity matching
            max_results: Maximum number of results to return
            
        Returns:
            List of similar configurations
            
        Raises:
            Exception: If an error occurs during the search
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("find_similar_configurations", 0.3))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception("Simulated error finding similar configurations")
        
        # Find similar configurations (simplified matching)
        results = []
        
        # Sort trail data by timestamp (newest first)
        sorted_trails = sorted(
            self.trail_data.values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        # Filter by capabilities (simplified matching)
        capability_set = set(capabilities)
        
        for trail in sorted_trails:
            # Skip inactive assemblies
            if trail.get("status") != "active":
                continue
            
            # TODO: In a real implementation, we would check if the cells in this trail
            # provide the requested capabilities. For simulation, we'll use simplified matching.
            
            # For simulation, assume match if number of cells is at least the number of capabilities
            if len(trail.get("cell_ids", [])) >= len(capabilities):
                config = {
                    "id": trail.get("quantum_signature", ""),
                    "cell_specs": [{"cell_type": cell_id} for cell_id in trail.get("cell_ids", [])],
                    "connection_map": trail.get("connection_map", {}),
                    "performance_score": self._calculate_performance_score(trail),
                    "timestamp": trail.get("timestamp", "")
                }
                results.append(config)
            
            if len(results) >= max_results:
                break
        
        logger.debug(f"Found {len(results)} similar configurations")
        
        return results
    
    def _calculate_performance_score(self, trail: Dict[str, Any]) -> float:
        """
        Calculate a performance score for a trail.
        
        Args:
            trail: Trail data
            
        Returns:
            Performance score (higher is better)
        """
        metrics = trail.get("performance_metrics", {})
        
        # Calculate a score based on available metrics
        score = 0.0
        
        # Assembly time (lower is better)
        assembly_time = metrics.get("assembly_time_ms", 1000)
        if assembly_time > 0:
            score += 1000 / assembly_time  # Inverse of assembly time
        
        # Usage time (higher might be better - indicates utility)
        usage_time = metrics.get("total_usage_time_ms", 0)
        if usage_time > 0:
            score += min(usage_time / 60000, 5)  # Cap at 5 points (5 minutes)
        
        # Memory efficiency (lower peak memory is better)
        memory_peak = metrics.get("memory_peak_mb", 1000)
        if memory_peak > 0:
            score += 1000 / memory_peak
        
        # CPU efficiency (lower average CPU is better)
        cpu_avg = metrics.get("cpu_usage_avg", 100)
        if cpu_avg > 0:
            score += 100 / cpu_avg
        
        return score


class SimulatedAssembler:
    """
    Simulates the QCC Assembler.
    
    The simulated assembler orchestrates simulated cells and interacts with
    other simulated components to provide a realistic testing environment.
    
    Attributes:
        id (str): Unique identifier for this assembler
        providers (List): List of simulated providers
        quantum_trail (SimulatedQuantumTrail): Simulated quantum trail
        active_solutions (Dict): Dictionary of active solutions
        latency (Dict): Configured latencies for assembler operations
        error_rate (float): Probability of introducing errors
    """
    
    def __init__(
        self,
        providers: List[SimulatedProvider] = None,
        quantum_trail: SimulatedQuantumTrail = None,
        latency: Dict[str, float] = None,
        error_rate: float = 0.0
    ):
        """
        Initialize a simulated assembler.
        
        Args:
            providers: List of simulated providers
            quantum_trail: Simulated quantum trail
            latency: Dictionary of operation latencies
            error_rate: Probability of errors (0.0 to 1.0)
        """
        self.id = str(uuid.uuid4())
        self.providers = providers or [SimulatedProvider()]
        self.quantum_trail = quantum_trail or SimulatedQuantumTrail()
        self.active_solutions = {}
        self.latency = latency or {
            "assemble_solution": 1.0,
            "release_solution": 0.5,
            "analyze_intent": 0.3
        }
        self.error_rate = error_rate
        
        # Assembler state
        self.total_assemblies = 0
        self.total_cells_requested = 0
        self.start_time = datetime.now()
        
        logger.debug(f"Created simulated assembler {self.id}")
    
    async def analyze_intent(
        self,
        user_request: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent to determine required capabilities.
        
        Args:
            user_request: Natural language user request
            context: Additional context information
            
        Returns:
            Intent analysis result
            
        Raises:
            Exception: If an error occurs during analysis
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("analyze_intent", 0.3))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception("Simulated error analyzing intent")
        
        # Simplified intent analysis
        # In a real system, this would use NLP and other techniques
        
        # Basic keyword matching for capabilities
        capabilities = []
        
        # Common scenarios
        if any(term in user_request.lower() for term in ["file", "folder", "document", "save", "open"]):
            capabilities.append("file_system")
        
        if any(term in user_request.lower() for term in ["write", "text", "document", "story", "essay"]):
            capabilities.append("text_generation")
        
        if any(term in user_request.lower() for term in ["show", "display", "ui", "interface", "form"]):
            capabilities.append("ui_rendering")
        
        if any(term in user_request.lower() for term in ["graph", "chart", "plot", "visualization", "data"]):
            capabilities.append("data_visualization")
        
        if any(term in user_request.lower() for term in ["network", "internet", "web", "connect", "online"]):
            capabilities.append("network_interface")
        
        # Default to text_generation if no clear capabilities identified
        if not capabilities:
            capabilities.append("text_generation")
        
        # Determine suggested connections
        suggested_connections = {}
        if len(capabilities) > 1:
            # Simple sequential connection pattern
            for i in range(len(capabilities) - 1):
                suggested_connections[capabilities[i]] = [capabilities[i + 1]]
        
        return {
            "user_request": user_request,
            "interpreted_intent": f"The user wants to {user_request}",
            "required_capabilities": capabilities,
            "suggested_connections": suggested_connections,
            "confidence": 0.85,
            "use_previous_configurations": True
        }
    
    async def assemble_solution(
        self,
        user_request: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Assemble a solution based on user intent.
        
        Args:
            user_request: Natural language user request
            context: Additional context information
            
        Returns:
            Assembled solution
            
        Raises:
            Exception: If an error occurs during assembly
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("assemble_solution", 1.0))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception("Simulated error assembling solution")
        
        try:
            # Update counters
            self.total_assemblies += 1
            
            # Prepare context
            context = context or {}
            context.update({
                "timestamp": datetime.now().isoformat(),
                "device_info": context.get("device_info", self._get_default_device_info()),
                "assembler_id": self.id
            })
            
            # Step 1: Analyze user intent
            intent_analysis = await self.analyze_intent(user_request, context)
            
            # Step 2: Generate quantum trail
            quantum_signature = await self.quantum_trail.generate_signature(
                user_id=context.get("user_id", "anonymous"),
                intent=intent_analysis,
                context=context
            )
            
            # Step 3: Try to find similar configurations in quantum trail
            similar_configs = []
            if intent_analysis.get("use_previous_configurations", True):
                similar_configs = await self.quantum_trail.find_similar_configurations(
                    capabilities=intent_analysis["required_capabilities"],
                    context_similarity=context,
                    max_results=3
                )
            
            # Step 4: Request cells
            cells = {}
            
            if similar_configs and len(similar_configs) > 0:
                # Use existing configuration as guide
                best_config = similar_configs[0]
                
                for cell_spec in best_config.get("cell_specs", []):
                    cell_type = cell_spec.get("cell_type")
                    
                    # Request from provider
                    provider = random.choice(self.providers)
                    cell = await provider.get_cell(
                        cell_type=cell_type,
                        version=cell_spec.get("version", "latest"),
                        quantum_signature=quantum_signature,
                        parameters=cell_spec.get("parameters", {})
                    )
                    
                    cells[cell.id] = cell
                    self.total_cells_requested += 1
            else:
                # Request based on capabilities
                for capability in intent_analysis["required_capabilities"]:
                    # Request from provider
                    provider = random.choice(self.providers)
                    cell = await provider.get_cell_for_capability(
                        capability=capability,
                        quantum_signature=quantum_signature,
                        context=context
                    )
                    
                    cells[cell.id] = cell
                    self.total_cells_requested += 1
            
            # Step 5: Initialize cells
            for cell_id, cell in cells.items():
                init_result = await cell.initialize({
                    "cell_id": cell_id,
                    "quantum_signature": quantum_signature,
                    "context": context
                })
                
                if init_result.get("status") != "success":
                    logger.warning(f"Cell {cell_id} initialization failed: {init_result.get('error')}")
            
            # Step 6: Establish connections
            connection_map = {}
            
            if similar_configs and len(similar_configs) > 0:
                # Use connection map from configuration
                config_connection_map = similar_configs[0].get("connection_map", {})
                
                # Translate old cell IDs to new cell IDs
                cell_by_type = {}
                for cell_id, cell in cells.items():
                    if cell.cell_type not in cell_by_type:
                        cell_by_type[cell.cell_type] = cell_id
                
                for source_type, target_types in config_connection_map.items():
                    if source_type in cell_by_type:
                        source_id = cell_by_type[source_type]
                        connection_map[source_id] = []
                        
                        for target_type in target_types:
                            if target_type in cell_by_type:
                                connection_map[source_id].append(cell_by_type[target_type])
            else:
                # Use suggested connections from intent analysis
                suggested_connections = intent_analysis.get("suggested_connections", {})
                
                # Translate capability-based connections to cell IDs
                cell_by_capability = {}
                for cell_id, cell in cells.items():
                    if cell.capability not in cell_by_capability:
                        cell_by_capability[cell.capability] = cell_id
                
                for source_capability, target_capabilities in suggested_connections.items():
                    if source_capability in cell_by_capability:
                        source_id = cell_by_capability[source_capability]
                        connection_map[source_id] = []
                        
                        for target_capability in target_capabilities:
                            if target_capability in cell_by_capability:
                                connection_map[source_id].append(cell_by_capability[target_capability])
            
            # Establish connections
            for source_id, target_ids in connection_map.items():
                if source_id in cells:
                    source_cell = cells[source_id]
                    
                    for target_id in target_ids:
                        if target_id in cells:
                            await source_cell.connect_to(target_id)
            
            # Step 7: Activate cells
            for cell_id, cell in cells.items():
                await cell.activate()
            
            # Step 8: Create solution
            solution_id = str(uuid.uuid4())
            solution = {
                "id": solution_id,
                "cells": {cell_id: cell.to_dict() for cell_id, cell in cells.items()},
                "quantum_signature": quantum_signature,
                "created_at": datetime.now().isoformat(),
                "intent": intent_analysis,
                "status": "active",
                "context": context,
                "connection_map": connection_map
            }
            
            # Store active solution
            self.active_solutions[solution_id] = {
                "solution": solution,
                "cells": cells,
                "quantum_signature": quantum_signature
            }
            
            # Step 9: Record assembly in quantum trail
            await self.quantum_trail.record_assembly(
                quantum_signature=quantum_signature,
                solution_id=solution_id,
                cell_ids=[cell.id for cell in cells.values()],
                connection_map=connection_map,
                performance_metrics={"assembly_time_ms": int(self.latency.get("assemble_solution", 1.0) * 1000)}
            )
            
            logger.info(f"Assembled solution {solution_id} with {len(cells)} cells")
            
            return solution
            
        except Exception as e:
            logger.error(f"Error assembling solution: {e}")
            raise Exception(f"Failed to assemble solution: {e}")
    
    async def release_solution(self, solution_id: str) -> bool:
        """
        Release a solution and its resources.
        
        Args:
            solution_id: Unique identifier for the solution
            
        Returns:
            Success indicator
            
        Raises:
            Exception: If the solution is not found or an error occurs
        """
        # Apply latency
        await asyncio.sleep(self.latency.get("release_solution", 0.5))
        
        # Check for random error
        if random.random() < self.error_rate:
            raise Exception(f"Simulated error releasing solution {solution_id}")
        
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise Exception(f"Solution not found: {solution_id}")
        
        solution_data = self.active_solutions[solution_id]
        cells = solution_data["cells"]
        quantum_signature = solution_data["quantum_signature"]
        
        # Deactivate and release cells
        for cell_id, cell in cells.items():
            try:
                await cell.deactivate()
                await cell.release()
            except Exception as e:
                logger.warning(f"Error releasing cell {cell_id}: {e}")
        
        # Update quantum trail
        await self.quantum_trail.update_assembly_record(
            quantum_signature=quantum_signature,
            solution_id=solution_id,
            status="released",
            performance_metrics={
                "total_usage_time_ms": self._calculate_usage_time(solution_data["solution"])
            }
        )
        
        # Remove from active solutions
        del self.active_solutions[solution_id]
        
        logger.info(f"Released solution {solution_id}")
        
        return True
    
    async def execute_cell_capability(
        self,
        solution_id: str,
        cell_id: str,
        capability: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a capability on a cell within a solution.
        
        Args:
            solution_id: Unique identifier for the solution
            cell_id: Identifier of the cell to execute
            capability: Capability to execute
            parameters: Capability parameters
            
        Returns:
            Capability execution result
            
        Raises:
            Exception: If the solution or cell is not found or an error occurs
        """
        # Check if solution exists
        if solution_id not in self.active_solutions:
            raise Exception(f"Solution not found: {solution_id}")
        
        # Get the solution
        solution_data = self.active_solutions[solution_id]
        cells = solution_data["cells"]
        
        # Check if cell exists
        if cell_id not in cells:
            raise Exception(f"Cell not found: {cell_id}")
        
        # Get the cell
        cell = cells[cell_id]
        
        # Execute capability
        result = await cell.execute_capability({
            "capability": capability,
            "parameters": parameters or {}
        })
        
        return result
    
    def _calculate_usage_time(self, solution: Dict[str, Any]) -> int:
        """
        Calculate the usage time for a solution in milliseconds.
        
        Args:
            solution: Solution data
            
        Returns:
            Usage time in milliseconds
        """
        created_at = datetime.fromisoformat(solution.get("created_at", datetime.now().isoformat()))
        usage_time_ms = int((datetime.now() - created_at).total_seconds() * 1000)
        return usage_time_ms
    
    def _get_default_device_info(self) -> Dict[str, Any]:
        """
        Get default device information.
        
        Returns:
            Dictionary with device information
        """
        return {
            "platform": "simulated",
            "memory_gb": 8,
            "cpu_cores": 4,
            "gpu_available": False
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the simulated assembler.
        
        Returns:
            Status information
        """
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "assembler_id": self.id,
            "status": "active",
            "uptime_seconds": uptime_seconds,
            "active_solutions": len(self.active_solutions),
            "total_assemblies": self.total_assemblies,
            "total_cells_requested": self.total_cells_requested,
            "error_rate": self.error_rate
        }


class SimulationScenario:
    """
    Defines a simulation scenario for testing.
    
    A scenario specifies the components, configurations, user requests,
    and expected outcomes for a simulation run.
    
    Attributes:
        name (str): Name of the scenario
        description (str): Description of the scenario
        providers (List): Provider configurations
        cells (Dict): Cell configurations
        quantum_trail (Dict): Quantum trail configuration
        assembler (Dict): Assembler configuration
        requests (List): Sequence of user requests to simulate
        expected_outcomes (Dict): Expected outcomes for validation
    """
    
    def __init__(
        self,
        name: str,
        description: str = None,
        providers: List[Dict[str, Any]] = None,
        cells: Dict[str, Dict[str, Any]] = None,
        quantum_trail: Dict[str, Any] = None,
        assembler: Dict[str, Any] = None,
        requests: List[Dict[str, Any]] = None,
        expected_outcomes: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ):
        """
        Initialize a simulation scenario.
        
        Args:
            name: Name of the scenario
            description: Description of the scenario
            providers: Provider configurations
            cells: Cell configurations
            quantum_trail: Quantum trail configuration
            assembler: Assembler configuration
            requests: Sequence of user requests to simulate
            expected_outcomes: Expected outcomes for validation
            context: Global context for all requests
        """
        self.name = name
        self.description = description or f"Simulation scenario: {name}"
        self.providers = providers or []
        self.cells = cells or {}
        self.quantum_trail = quantum_trail or {}
        self.assembler = assembler or {}
        self.requests = requests or []
        self.expected_outcomes = expected_outcomes or {}
        self.context = context or {}
        
        logger.debug(f"Created simulation scenario: {name}")
    
    @classmethod
    def from_file(cls, file_path: str) -> 'SimulationScenario':
        """
        Create a scenario from a YAML or JSON file.
        
        Args:
            file_path: Path to the scenario file
            
        Returns:
            SimulationScenario instance
            
        Raises:
            Exception: If the file cannot be loaded
        """
        try:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
            elif file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
            else:
                raise Exception(f"Unsupported file type: {file_path}")
            
            return cls(**data)
            
        except Exception as e:
            logger.error(f"Error loading scenario from {file_path}: {e}")
            raise Exception(f"Failed to load scenario: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the scenario to a dictionary.
        
        Returns:
            Dictionary representation of the scenario
        """
        return {
            "name": self.name,
            "description": self.description,
            "providers": self.providers,
            "cells": self.cells,
            "quantum_trail": self.quantum_trail,
            "assembler": self.assembler,
            "requests": self.requests,
            "expected_outcomes": self.expected_outcomes,
            "context": self.context
        }
    
    def save(self, file_path: str) -> None:
        """
        Save the scenario to a file.
        
        Args:
            file_path: Path to save the scenario
            
        Raises:
            Exception: If the file cannot be saved
        """
        try:
            data = self.to_dict()
            
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                with open(file_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            elif file_path.endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                file_path += '.yaml'
                with open(file_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            
            logger.info(f"Scenario saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving scenario to {file_path}: {e}")
            raise Exception(f"Failed to save scenario: {e}")


class SimulationRecording:
    """
    Records and replays simulation events.
    
    The recording captures all events and interactions during a simulation
    run, allowing them to be saved, analyzed, and replayed later.
    
    Attributes:
        id (str): Unique identifier for this recording
        scenario_name (str): Name of the scenario being recorded
        events (List): List of recorded events
        start_time (datetime): Time when recording started
        end_time (datetime): Time when recording ended
        metadata (Dict): Additional metadata about the recording
    """
    
    def __init__(
        self,
        scenario_name: str = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Initialize a simulation recording.
        
        Args:
            scenario_name: Name of the scenario being recorded
            metadata: Additional metadata about the recording
        """
        self.id = str(uuid.uuid4())
        self.scenario_name = scenario_name or "unnamed_scenario"
        self.events = []
        self.start_time = datetime.now()
        self.end_time = None
        self.metadata = metadata or {}
        
        logger.debug(f"Started recording {self.id} for scenario {scenario_name}")
    
    def record_event(
        self,
        event_type: str,
        component: str,
        action: str,
        data: Dict[str, Any] = None,
        result: Dict[str, Any] = None,
        error: str = None
    ) -> None:
        """
        Record a simulation event.
        
        Args:
            event_type: Type of event (request, response, error)
            component: Component involved (assembler, provider, cell)
            action: Action performed
            data: Event data
            result: Action result
            error: Error message if applicable
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "component": component,
            "action": action,
            "data": data,
            "result": result,
            "error": error
        }
        
        self.events.append(event)
    
    def complete_recording(self) -> None:
        """Complete the recording and set the end time."""
        self.end_time = datetime.now()
        logger.debug(f"Completed recording {self.id} with {len(self.events)} events")
    
    def save(self, file_path: str = None) -> str:
        """
        Save the recording to a file.
        
        Args:
            file_path: Path to save the recording
            
        Returns:
            Path to the saved recording
            
        Raises:
            Exception: If the recording cannot be saved
        """
        if not self.end_time:
            self.complete_recording()
        
        # Create default file path if not provided
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scenario_name = self.scenario_name.replace(" ", "_").lower()
            file_path = f"recordings/{scenario_name}_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            # Prepare recording data
            recording_data = {
                "id": self.id,
                "scenario_name": self.scenario_name,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_seconds": (self.end_time - self.start_time).total_seconds(),
                "event_count": len(self.events),
                "metadata": self.metadata,
                "events": self.events
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(recording_data, f, indent=2)
            
            logger.info(f"Recording saved to {file_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving recording to {file_path}: {e}")
            raise Exception(f"Failed to save recording: {e}")
    
    @classmethod
    def load(cls, file_path: str) -> 'SimulationRecording':
        """
        Load a recording from a file.
        
        Args:
            file_path: Path to the recording file
            
        Returns:
            SimulationRecording instance
            
        Raises:
            Exception: If the recording cannot be loaded
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            recording = cls(
                scenario_name=data.get("scenario_name", "unknown"),
                metadata=data.get("metadata", {})
            )
            
            recording.id = data.get("id", str(uuid.uuid4()))
            recording.events = data.get("events", [])
            recording.start_time = datetime.fromisoformat(data.get("start_time", recording.start_time.isoformat()))
            recording.end_time = datetime.fromisoformat(data.get("end_time", datetime.now().isoformat()))
            
            logger.info(f"Loaded recording {recording.id} with {len(recording.events)} events")
            
            return recording
            
        except Exception as e:
            logger.error(f"Error loading recording from {file_path}: {e}")
            raise Exception(f"Failed to load recording: {e}")
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze the recording to extract metrics and insights.
        
        Returns:
            Dictionary of analysis results
        """
        if not self.events:
            return {"error": "No events to analyze"}
        
        try:
            # Initialize analysis
            analysis = {
                "events_count": len(self.events),
                "event_types": {},
                "components": {},
                "actions": {},
                "errors": [],
                "solutions": {},
                "cells": {},
                "performance": {
                    "assembler": {
                        "assemble_solution_times": [],
                        "release_solution_times": []
                    },
                    "cells": {
                        "initialization_times": [],
                        "activation_times": [],
                        "execution_times": []
                    }
                }
            }
            
            # Analyze events
            for event in self.events:
                # Count event types
                event_type = event.get("event_type", "unknown")
                if event_type not in analysis["event_types"]:
                    analysis["event_types"][event_type] = 0
                analysis["event_types"][event_type] += 1
                
                # Count components
                component = event.get("component", "unknown")
                if component not in analysis["components"]:
                    analysis["components"][component] = 0
                analysis["components"][component] += 1
                
                # Count actions
                action = event.get("action", "unknown")
                if action not in analysis["actions"]:
                    analysis["actions"][action] = 0
                analysis["actions"][action] += 1
                
                # Record errors
                if event.get("error"):
                    analysis["errors"].append({
                        "timestamp": event.get("timestamp"),
                        "component": component,
                        "action": action,
                        "error": event.get("error")
                    })
                
                # Track solutions
                if action == "assemble_solution" and event.get("result"):
                    solution_id = event.get("result", {}).get("id")
                    if solution_id:
                        if solution_id not in analysis["solutions"]:
                            analysis["solutions"][solution_id] = {
                                "cells": [],
                                "created_at": event.get("timestamp"),
                                "released_at": None
                            }
                        
                        # Record cells
                        cells = event.get("result", {}).get("cells", {})
                        if cells:
                            analysis["solutions"][solution_id]["cells"] = list(cells.keys())
                            
                            # Track cell types
                            for cell_id, cell_data in cells.items():
                                cell_type = cell_data.get("cell_type", "unknown")
                                if cell_type not in analysis["cells"]:
                                    analysis["cells"][cell_type] = 0
                                analysis["cells"][cell_type] += 1
                
                # Track solution release
                if action == "release_solution" and event.get("data"):
                    solution_id = event.get("data", {}).get("solution_id")
                    if solution_id and solution_id in analysis["solutions"]:
                        analysis["solutions"][solution_id]["released_at"] = event.get("timestamp")
                
                # Track performance metrics
                if component == "assembler" and action == "assemble_solution":
                    if event.get("result"):
                        start_time = datetime.fromisoformat(event.get("timestamp"))
                        # Calculate approximate assembly time from event timestamps
                        next_event_idx = self.events.index(event) + 1
                        if next_event_idx < len(self.events):
                            next_event = self.events[next_event_idx]
                            end_time = datetime.fromisoformat(next_event.get("timestamp"))
                            assembly_time_ms = (end_time - start_time).total_seconds() * 1000
                            analysis["performance"]["assembler"]["assemble_solution_times"].append(assembly_time_ms)
                
                if component == "assembler" and action == "release_solution":
                    if event.get("result"):
                        start_time = datetime.fromisoformat(event.get("timestamp"))
                        next_event_idx = self.events.index(event) + 1
                        if next_event_idx < len(self.events):
                            next_event = self.events[next_event_idx]
                            end_time = datetime.fromisoformat(next_event.get("timestamp"))
                            release_time_ms = (end_time - start_time).total_seconds() * 1000
                            analysis["performance"]["assembler"]["release_solution_times"].append(release_time_ms)
                
                if component == "cell" and action == "initialize":
                    if event.get("result"):
                        start_time = datetime.fromisoformat(event.get("timestamp"))
                        next_event_idx = self.events.index(event) + 1
                        if next_event_idx < len(self.events):
                            next_event = self.events[next_event_idx]
                            end_time = datetime.fromisoformat(next_event.get("timestamp"))
                            init_time_ms = (end_time - start_time).total_seconds() * 1000
                            analysis["performance"]["cells"]["initialization_times"].append(init_time_ms)
                
                if component == "cell" and action == "activate":
                    if event.get("result"):
                        start_time = datetime.fromisoformat(event.get("timestamp"))
                        next_event_idx = self.events.index(event) + 1
                        if next_event_idx < len(self.events):
                            next_event = self.events[next_event_idx]
                            end_time = datetime.fromisoformat(next_event.get("timestamp"))
                            activate_time_ms = (end_time - start_time).total_seconds() * 1000
                            analysis["performance"]["cells"]["activation_times"].append(activate_time_ms)
                
                if component == "cell" and action == "execute_capability":
                    if event.get("result"):
                        metrics = event.get("result", {}).get("performance_metrics", {})
                        execution_time_ms = metrics.get("execution_time_ms")
                        if execution_time_ms:
                            analysis["performance"]["cells"]["execution_times"].append(execution_time_ms)
            
            # Calculate averages
            if analysis["performance"]["assembler"]["assemble_solution_times"]:
                analysis["performance"]["assembler"]["avg_assemble_time_ms"] = sum(
                    analysis["performance"]["assembler"]["assemble_solution_times"]
                ) / len(analysis["performance"]["assembler"]["assemble_solution_times"])
            
            if analysis["performance"]["assembler"]["release_solution_times"]:
                analysis["performance"]["assembler"]["avg_release_time_ms"] = sum(
                    analysis["performance"]["assembler"]["release_solution_times"]
                ) / len(analysis["performance"]["assembler"]["release_solution_times"])
            
            if analysis["performance"]["cells"]["initialization_times"]:
                analysis["performance"]["cells"]["avg_init_time_ms"] = sum(
                    analysis["performance"]["cells"]["initialization_times"]
                ) / len(analysis["performance"]["cells"]["initialization_times"])
            
            if analysis["performance"]["cells"]["activation_times"]:
                analysis["performance"]["cells"]["avg_activation_time_ms"] = sum(
                    analysis["performance"]["cells"]["activation_times"]
                ) / len(analysis["performance"]["cells"]["activation_times"])
            
            if analysis["performance"]["cells"]["execution_times"]:
                analysis["performance"]["cells"]["avg_execution_time_ms"] = sum(
                    analysis["performance"]["cells"]["execution_times"]
                ) / len(analysis["performance"]["cells"]["execution_times"])
            
            # Calculate solution lifetimes
            solution_lifetimes = []
            for solution_id, solution_data in analysis["solutions"].items():
                if solution_data.get("created_at") and solution_data.get("released_at"):
                    created = datetime.fromisoformat(solution_data["created_at"])
                    released = datetime.fromisoformat(solution_data["released_at"])
                    lifetime_seconds = (released - created).total_seconds()
                    solution_lifetimes.append(lifetime_seconds)
            
            if solution_lifetimes:
                analysis["solutions"]["avg_lifetime_seconds"] = sum(solution_lifetimes) / len(solution_lifetimes)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing recording: {e}")
            return {"error": f"Analysis failed: {str(e)}"}


class Simulator:
    """
    Main simulator class that orchestrates simulation runs.
    
    The simulator creates and manages all components, executes scenarios,
    records events, and analyzes results.
    
    Attributes:
        id (str): Unique identifier for this simulator instance
        scenarios_dir (str): Directory containing scenario files
        recordings_dir (str): Directory for saving recordings
        active_scenario (SimulationScenario): Currently active scenario
        recording (SimulationRecording): Current recording if active
    """
    
    def __init__(
        self,
        scenarios_dir: str = None,
        recordings_dir: str = None
    ):
        """
        Initialize the simulator.
        
        Args:
            scenarios_dir: Directory containing scenario files
            recordings_dir: Directory for saving recordings
        """
        self.id = str(uuid.uuid4())
        self.scenarios_dir = scenarios_dir or os.path.join(os.getcwd(), "scenarios")
        self.recordings_dir = recordings_dir or os.path.join(os.getcwd(), "recordings")
        self.active_scenario = None
        self.recording = None
        
        # Ensure directories exist
        os.makedirs(self.scenarios_dir, exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        logger.info(f"Simulator initialized with ID {self.id}")
        logger.info(f"Using scenarios directory: {self.scenarios_dir}")
        logger.info(f"Using recordings directory: {self.recordings_dir}")
    
    def list_scenarios(self) -> List[str]:
        """
        List available scenario files.
        
        Returns:
            List of scenario file paths
        """
        scenario_files = []
        
        for file in os.listdir(self.scenarios_dir):
            if file.endswith('.yaml') or file.endswith('.yml') or file.endswith('.json'):
                scenario_files.append(os.path.join(self.scenarios_dir, file))
        
        return scenario_files
    
    def list_recordings(self) -> List[str]:
        """
        List available recording files.
        
        Returns:
            List of recording file paths
        """
        recording_files = []
        
        for file in os.listdir(self.recordings_dir):
            if file.endswith('.json'):
                recording_files.append(os.path.join(self.recordings_dir, file))
        
        return recording_files
    
    def load_scenario(self, scenario_path: str) -> SimulationScenario:
        """
        Load a scenario from a file.
        
        Args:
            scenario_path: Path to the scenario file
            
        Returns:
            Loaded scenario
            
        Raises:
            Exception: If the scenario cannot be loaded
        """
        try:
            scenario = SimulationScenario.from_file(scenario_path)
            self.active_scenario = scenario
            logger.info(f"Loaded scenario: {scenario.name}")
            return scenario
        except Exception as e:
            logger.error(f"Error loading scenario: {e}")
            raise Exception(f"Failed to load scenario: {e}")
    
    async def run_scenario(
        self,
        scenario: SimulationScenario = None,
        record: bool = True
    ) -> Dict[str, Any]:
        """
        Run a simulation scenario.
        
        Args:
            scenario: Scenario to run (uses active scenario if None)
            record: Whether to record the simulation
            
        Returns:
            Simulation results
            
        Raises:
            Exception: If the scenario cannot be run
        """
        # Use active scenario if none provided
        if scenario is None:
            scenario = self.active_scenario
        
        if scenario is None:
            raise Exception("No scenario specified and no active scenario")
        
        logger.info(f"Running scenario: {scenario.name}")
        
        # Start recording if enabled
        if record:
            self.recording = SimulationRecording(
                scenario_name=scenario.name,
                metadata={"description": scenario.description}
            )
        
        try:
            # Setup components
            assembler = await self._setup_assembler(scenario)
            
            results = {
                "scenario_name": scenario.name,
                "start_time": datetime.now().isoformat(),
                "solutions": [],
                "errors": []
            }
            
            # Process requests
            for i, request_config in enumerate(scenario.requests):
                request = request_config.get("request", "")
                
                if not request:
                    logger.warning(f"Empty request at index {i}, skipping")
                    continue
                
                # Prepare context
                context = copy.deepcopy(scenario.context)
                request_context = request_config.get("context", {})
                if request_context:
                    self._merge_dicts(context, request_context)
                
                logger.info(f"Processing request ({i+1}/{len(scenario.requests)}): {request}")
                
                if record:
                    self.recording.record_event(
                        event_type="request",
                        component="simulator",
                        action="process_request",
                        data={"request": request, "context": context}
                    )
                
                try:
                    # Process the request
                    solution = await assembler.assemble_solution(request, context)
                    
                    if record:
                        self.recording.record_event(
                            event_type="response",
                            component="assembler",
                            action="assemble_solution",
                            result=solution
                        )
                    
                    # Store solution result
                    solution_result = {
                        "solution_id": solution.get("id"),
                        "request": request,
                        "cell_count": len(solution.get("cells", {})),
                        "status": "assembled"
                    }
                    
                    results["solutions"].append(solution_result)
                    
                    # Check if we should execute capabilities
                    executions = request_config.get("executions", [])
                    for execution in executions:
                        cell_id = execution.get("cell_id")
                        capability = execution.get("capability")
                        params = execution.get("parameters", {})
                        
                        if not cell_id:
                            # If no specific cell ID, find a cell with the requested capability
                            for cid, cell_data in solution.get("cells", {}).items():
                                if cell_data.get("capability") == capability:
                                    cell_id = cid
                                    break
                        
                        if cell_id and capability:
                            logger.info(f"Executing capability {capability} on cell {cell_id}")
                            
                            try:
                                execution_result = await assembler.execute_cell_capability(
                                    solution_id=solution.get("id"),
                                    cell_id=cell_id,
                                    capability=capability,
                                    parameters=params
                                )
                                
                                if record:
                                    self.recording.record_event(
                                        event_type="response",
                                        component="cell",
                                        action="execute_capability",
                                        data={
                                            "solution_id": solution.get("id"),
                                            "cell_id": cell_id,
                                            "capability": capability,
                                            "parameters": params
                                        },
                                        result=execution_result
                                    )
                                
                            except Exception as e:
                                logger.error(f"Error executing capability: {e}")
                                
                                if record:
                                    self.recording.record_event(
                                        event_type="error",
                                        component="cell",
                                        action="execute_capability",
                                        data={
                                            "solution_id": solution.get("id"),
                                            "cell_id": cell_id,
                                            "capability": capability,
                                            "parameters": params
                                        },
                                        error=str(e)
                                    )
                    
                    # Check if we should release the solution
                    if request_config.get("release_after", True):
                        logger.info(f"Releasing solution {solution.get('id')}")
                        
                        try:
                            await assembler.release_solution(solution.get("id"))
                            solution_result["status"] = "released"
                            
                            if record:
                                self.recording.record_event(
                                    event_type="response",
                                    component="assembler",
                                    action="release_solution",
                                    data={"solution_id": solution.get("id")},
                                    result={"success": True}
                                )
                            
                        except Exception as e:
                            logger.error(f"Error releasing solution: {e}")
                            solution_result["status"] = "release_failed"
                            
                            if record:
                                self.recording.record_event(
                                    event_type="error",
                                    component="assembler",
                                    action="release_solution",
                                    data={"solution_id": solution.get("id")},
                                    error=str(e)
                                )
                
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    results["errors"].append({
                        "request": request,
                        "error": str(e)
                    })
                    
                    if record:
                        self.recording.record_event(
                            event_type="error",
                            component="assembler",
                            action="assemble_solution",
                            data={"request": request, "context": context},
                            error=str(e)
                        )
            
            # Complete the simulation
            results["end_time"] = datetime.now().isoformat()
            start_time = datetime.fromisoformat(results["start_time"])
            end_time = datetime.fromisoformat(results["end_time"])
            results["duration_seconds"] = (end_time - start_time).total_seconds()
            results["success_rate"] = len(results["solutions"]) / len(scenario.requests) if scenario.requests else 0
            results["error_count"] = len(results["errors"])
            
            # Get assembler status
            try:
                assembler_status = await assembler.get_status()
                results["assembler_status"] = assembler_status
            except Exception as e:
                logger.error(f"Error getting assembler status: {e}")
            
            # Complete recording
            if record:
                self.recording.complete_recording()
                recording_path = self.recording.save(
                    os.path.join(self.recordings_dir, f"{scenario.name.replace(' ', '_').lower()}_{int(time.time())}.json")
                )
                results["recording_path"] = recording_path
            
            logger.info(f"Scenario completed with {results['success_rate']*100:.1f}% success rate")
            
            return results
            
        except Exception as e:
            logger.error(f"Error running scenario: {e}")
            
            if record:
                self.recording.record_event(
                    event_type="error",
                    component="simulator",
                    action="run_scenario",
                    error=str(e)
                )
                self.recording.complete_recording()
                self.recording.save(
                    os.path.join(self.recordings_dir, f"error_{int(time.time())}.json")
                )
            
            raise Exception(f"Failed to run scenario: {e}")
    
    async def replay_recording(
        self,
        recording_path: str,
        interactive: bool = False,
        speed: float = 1.0
    ) -> None:
        """
        Replay a recorded simulation.
        
        Args:
            recording_path: Path to the recording file
            interactive: Whether to pause between events
            speed: Playback speed multiplier
            
        Raises:
            Exception: If the recording cannot be replayed
        """
        try:
            # Load recording
            recording = SimulationRecording.load(recording_path)
            logger.info(f"Replaying recording {recording.id} with {len(recording.events)} events")
            
            # Process events
            last_timestamp = None
            
            for i, event in enumerate(recording.events):
                # Print event info
                timestamp = event.get("timestamp", "")
                event_type = event.get("event_type", "unknown")
                component = event.get("component", "unknown")
                action = event.get("action", "unknown")
                
                print(f"\n[{i+1}/{len(recording.events)}] {timestamp} - {event_type.upper()} - {component}.{action}")
                
                # Calculate delay
                if last_timestamp and speed > 0:
                    last_time = datetime.fromisoformat(last_timestamp)
                    current_time = datetime.fromisoformat(timestamp)
                    delay = (current_time - last_time).total_seconds() / speed
                    
                    # Only delay if positive
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                last_timestamp = timestamp
                
                # Display event details
                if event.get("data"):
                    data_str = json.dumps(event["data"], indent=2)
                    print(f"Data: {data_str[:200]}..." if len(data_str) > 200 else f"Data: {data_str}")
                
                if event.get("result"):
                    result_str = json.dumps(event["result"], indent=2)
                    print(f"Result: {result_str[:200]}..." if len(result_str) > 200 else f"Result: {result_str}")
                
                if event.get("error"):
                    print(f"Error: {event['error']}")
                
                # Interactive mode
                if interactive:
                    input("Press Enter to continue...")
            
            logger.info("Replay completed")
            
        except Exception as e:
            logger.error(f"Error replaying recording: {e}")
            raise Exception(f"Failed to replay recording: {e}")
    
    async def analyze_recording(self, recording_path: str) -> Dict[str, Any]:
        """
        Analyze a recording file.
        
        Args:
            recording_path: Path to the recording file
            
        Returns:
            Analysis results
            
        Raises:
            Exception: If the recording cannot be analyzed
        """
        try:
            # Load recording
            recording = SimulationRecording.load(recording_path)
            logger.info(f"Analyzing recording {recording.id} with {len(recording.events)} events")
            
            # Perform analysis
            analysis = recording.analyze()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing recording: {e}")
            raise Exception(f"Failed to analyze recording: {e}")
    
    async def _setup_assembler(self, scenario: SimulationScenario) -> SimulatedAssembler:
        """
        Set up a simulated assembler based on scenario configuration.
        
        Args:
            scenario: Simulation scenario
            
        Returns:
            Configured SimulatedAssembler instance
        """
        # Create providers
        providers = []
        
        # Create provider instances
        for provider_config in scenario.providers:
            provider_name = provider_config.get("name", "provider")
            
            # Get provider-specific cells
            provider_cells = {}
            for cell_id, cell_config in scenario.cells.items():
                if cell_config.get("provider") == provider_name:
                    provider_cells[cell_id] = cell_config
            
            # Create provider
            provider = SimulatedProvider(
                name=provider_name,
                cells=provider_cells,
                latency=provider_config.get("latency", {}),
                error_rate=provider_config.get("error_rate", 0.0)
            )
            
            providers.append(provider)
        
        # If no providers defined, create a default one with all cells
        if not providers:
            provider = SimulatedProvider(
                name="default_provider",
                cells=scenario.cells,
                latency=scenario.quantum_trail.get("latency", {}),
                error_rate=scenario.quantum_trail.get("error_rate", 0.0)
            )
            providers.append(provider)
        
        # Create quantum trail
        quantum_trail = SimulatedQuantumTrail(
            latency=scenario.quantum_trail.get("latency", {}),
            error_rate=scenario.quantum_trail.get("error_rate", 0.0)
        )
        
        # Create assembler
        assembler = SimulatedAssembler(
            providers=providers,
            quantum_trail=quantum_trail,
            latency=scenario.assembler.get("latency", {}),
            error_rate=scenario.assembler.get("error_rate", 0.0)
        )
        
        return assembler
    
    def _merge_dicts(self, base: Dict, update: Dict) -> None:
        """
        Recursively merge dictionaries, updating base in place.
        
        Args:
            base: Base dictionary to update
            update: Dictionary with updates
        """
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_dicts(base[key], value)
            else:
                base[key] = value
    
    def create_default_scenario(self, name: str = "default_scenario") -> SimulationScenario:
        """
        Create a default scenario for testing.
        
        Args:
            name: Name for the scenario
            
        Returns:
            SimulationScenario instance
        """
        # Define default cells
        cells = {
            "file_system": {
                "cell_type": "file_system",
                "capability": "file_system",
                "version": "1.0.0",
                "provider": "default_provider",
                "resource_usage": {
                    "memory_mb": 30,
                    "cpu_percent": 2,
                    "storage_mb": 100
                }
            },
            "text_generation": {
                "cell_type": "text_generation",
                "capability": "text_generation",
                "version": "1.0.0",
                "provider": "default_provider",
                "resource_usage": {
                    "memory_mb": 200,
                    "cpu_percent": 30,
                    "storage_mb": 50
                }
            },
            "ui_rendering": {
                "cell_type": "ui_rendering",
                "capability": "ui_rendering",
                "version": "1.0.0",
                "provider": "default_provider",
                "resource_usage": {
                    "memory_mb": 80,
                    "cpu_percent": 15,
                    "storage_mb": 20
                }
            }
        }
        
        # Define provider
        providers = [
            {
                "name": "default_provider",
                "latency": {
                    "get_cell": 0.2,
                    "get_cell_for_capability": 0.3
                },
                "error_rate": 0.0
            }
        ]
        
        # Define requests
        requests = [
            {
                "request": "Write a short story about quantum computing",
                "context": {
                    "device_info": {
                        "platform": "windows",
                        "memory_gb": 16,
                        "cpu_cores": 8
                    }
                },
                "executions": [
                    {
                        "capability": "text_generation",
                        "parameters": {
                            "topic": "quantum computing",
                            "length": "short"
                        }
                    }
                ],
                "release_after": True
            },
            {
                "request": "Show me a form to enter my personal information",
                "context": {
                    "device_info": {
                        "platform": "web",
                        "memory_gb": 8,
                        "cpu_cores": 4
                    }
                },
                "executions": [
                    {
                        "capability": "ui_rendering",
                        "parameters": {
                            "form_type": "personal_info"
                        }
                    }
                ],
                "release_after": True
            },
            {
                "request": "Save my document to a file",
                "context": {
                    "device_info": {
                        "platform": "macos",
                        "memory_gb": 32,
                        "cpu_cores": 8
                    }
                },
                "executions": [
                    {
                        "capability": "file_system",
                        "parameters": {
                            "action": "save",
                            "filename": "document.txt",
                            "content": "This is my document content."
                        }
                    }
                ],
                "release_after": True
            }
        ]
        
        # Create scenario
        scenario = SimulationScenario(
            name=name,
            description="Default testing scenario with basic capabilities",
            providers=providers,
            cells=cells,
            quantum_trail={
                "latency": {
                    "generate_signature": 0.1,
                    "record_assembly": 0.2,
                    "find_similar_configurations": 0.3
                },
                "error_rate": 0.0
            },
            assembler={
                "latency": {
                    "assemble_solution": 1.0,
                    "release_solution": 0.5,
                    "analyze_intent": 0.3
                },
                "error_rate": 0.0
            },
            requests=requests,
            context={
                "user_id": "anonymous",
                "session_id": str(uuid.uuid4()),
                "environment": {
                    "type": "desktop",
                    "locale": "en-US",
                    "timezone": "UTC"
                }
            }
        )
        
        # Save scenario
        scenario_path = os.path.join(self.scenarios_dir, f"{name.replace(' ', '_').lower()}.yaml")
        scenario.save(scenario_path)
        
        logger.info(f"Created default scenario: {name}")
        logger.info(f"Saved to: {scenario_path}")
        
        return scenario


async def main():
    """
    Main function for command-line operation.
    """
    parser = argparse.ArgumentParser(description="QCC Simulation Environment")
    
    # Main command groups
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Scenario commands
    scenario_parser = subparsers.add_parser("scenario", help="Scenario management")
    scenario_subparsers = scenario_parser.add_subparsers(dest="scenario_command")
    
    # List scenarios
    list_parser = scenario_subparsers.add_parser("list", help="List available scenarios")
    
    # Create scenario
    create_parser = scenario_subparsers.add_parser("create", help="Create a new scenario")
    create_parser.add_argument("--name", required=True, help="Scenario name")
    
    # Run scenario
    run_parser = scenario_subparsers.add_parser("run", help="Run a scenario")
    run_parser.add_argument("--path", required=True, help="Path to scenario file")
    run_parser.add_argument("--no-record", action="store_true", help="Disable recording")
    
    # Recording commands
    recording_parser = subparsers.add_parser("recording", help="Recording management")
    recording_subparsers = recording_parser.add_subparsers(dest="recording_command")
    
    # List recordings
    recording_list_parser = recording_subparsers.add_parser("list", help="List available recordings")
    
    # Replay recording
    replay_parser = recording_subparsers.add_parser("replay", help="Replay a recording")
    replay_parser.add_argument("--path", required=True, help="Path to recording file")
    replay_parser.add_argument("--interactive", action="store_true", help="Interactive replay mode")
    replay_parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    
    # Analyze recording
    analyze_parser = recording_subparsers.add_parser("analyze", help="Analyze a recording")
    analyze_parser.add_argument("--path", required=True, help="Path to recording file")
    analyze_parser.add_argument("--output", help="Path to save analysis results")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize simulator
    simulator = Simulator()
    
    # Process commands
    if args.command == "scenario":
        if args.scenario_command == "list":
            scenarios = simulator.list_scenarios()
            print(f"Available scenarios ({len(scenarios)}):")
            for i, scenario_path in enumerate(scenarios):
                try:
                    scenario = SimulationScenario.from_file(scenario_path)
                    print(f"  {i+1}. {scenario.name} - {scenario.description}")
                    print(f"     Path: {scenario_path}")
                    print(f"     Requests: {len(scenario.requests)}")
                    print()
                except Exception as e:
                    print(f"  {i+1}. Error loading {scenario_path}: {e}")
                    print()
        
        elif args.scenario_command == "create":
            scenario = simulator.create_default_scenario(args.name)
            print(f"Created scenario: {scenario.name}")
            print(f"Description: {scenario.description}")
            print(f"Cells: {len(scenario.cells)}")
            print(f"Requests: {len(scenario.requests)}")
            print(f"Saved to: {os.path.join(simulator.scenarios_dir, f'{args.name.replace(' ', '_').lower()}.yaml')}")
        
        elif args.scenario_command == "run":
            scenario = simulator.load_scenario(args.path)
            print(f"Running scenario: {scenario.name}")
            print(f"Description: {scenario.description}")
            print(f"Requests: {len(scenario.requests)}")
            print()
            
            results = await simulator.run_scenario(scenario, not args.no_record)
            
            print("\nResults:")
            print(f"  Success rate: {results['success_rate']*100:.1f}%")
            print(f"  Duration: {results['duration_seconds']:.2f} seconds")
            print(f"  Solutions: {len(results['solutions'])}")
            print(f"  Errors: {len(results['errors'])}")
            
            if "recording_path" in results:
                print(f"\nRecording saved to: {results['recording_path']}")
    
    elif args.command == "recording":
        if args.recording_command == "list":
            recordings = simulator.list_recordings()
            print(f"Available recordings ({len(recordings)}):")
            for i, recording_path in enumerate(recordings):
                try:
                    recording = SimulationRecording.load(recording_path)
                    print(f"  {i+1}. {recording.scenario_name}")
                    print(f"     Path: {recording_path}")
                    print(f"     Events: {len(recording.events)}")
                    print(f"     Start: {recording.start_time}")
                    if recording.end_time:
                        duration = (recording.end_time - recording.start_time).total_seconds()
                        print(f"     Duration: {duration:.2f} seconds")
                    print()
                except Exception as e:
                    print(f"  {i+1}. Error loading {recording_path}: {e}")
                    print()
        
        elif args.recording_command == "replay":
            print(f"Replaying recording: {args.path}")
            print(f"Interactive mode: {args.interactive}")
            print(f"Speed: {args.speed}x")
            print()
            
            await simulator.replay_recording(args.path, args.interactive, args.speed)
        
        elif args.recording_command == "analyze":
            print(f"Analyzing recording: {args.path}")
            
            analysis = await simulator.analyze_recording(args.path)
            
            print("\nAnalysis Results:")
            print(f"  Events: {analysis.get('events_count', 0)}")
            print(f"  Event types: {analysis.get('event_types', {})}")
            print(f"  Components: {analysis.get('components', {})}")
            print(f"  Errors: {len(analysis.get('errors', []))}")
            
            if "performance" in analysis:
                perf = analysis["performance"]
                if "assembler" in perf:
                    assembler_perf = perf["assembler"]
                    print("\nAssembler Performance:")
                    if "avg_assemble_time_ms" in assembler_perf:
                        print(f"  Average assembly time: {assembler_perf['avg_assemble_time_ms']:.2f} ms")
                    if "avg_release_time_ms" in assembler_perf:
                        print(f"  Average release time: {assembler_perf['avg_release_time_ms']:.2f} ms")
                
                if "cells" in perf:
                    cell_perf = perf["cells"]
                    print("\nCell Performance:")
                    if "avg_init_time_ms" in cell_perf:
                        print(f"  Average initialization time: {cell_perf['avg_init_time_ms']:.2f} ms")
                    if "avg_activation_time_ms" in cell_perf:
                        print(f"  Average activation time: {cell_perf['avg_activation_time_ms']:.2f} ms")
                    if "avg_execution_time_ms" in cell_perf:
                        print(f"  Average execution time: {cell_perf['avg_execution_time_ms']:.2f} ms")
            
            if "solutions" in analysis and "avg_lifetime_seconds" in analysis["solutions"]:
                print(f"\nAverage solution lifetime: {analysis['solutions']['avg_lifetime_seconds']:.2f} seconds")
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2)
                print(f"\nAnalysis saved to: {args.output}")
    
    # If no command provided, show help
    if not args.command:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())

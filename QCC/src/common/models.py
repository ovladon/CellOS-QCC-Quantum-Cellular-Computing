"""
Data models for the Quantum Cellular Computing (QCC) system.

This module defines the core data structures used throughout the QCC
architecture, ensuring consistent representation of key entities.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import uuid
import hashlib

@dataclass
class Cell:
    """
    Represents a cell in the QCC system.
    
    A cell is a specialized mini language model with specific capabilities
    that can be dynamically assembled with other cells to fulfill user needs.
    
    Attributes:
        id: Unique identifier for the cell
        cell_type: Type of the cell
        capability: Primary capability provided by the cell
        version: Cell version
        provider: Provider that supplied the cell
        quantum_signature: Security signature for verification
        status: Current status of the cell
        created_at: Creation timestamp
        context: Context in which the cell was created
        parameters: Cell-specific parameters
        resource_usage: Resource consumption metrics
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cell_type: str = ""
    capability: str = ""
    version: str = "1.0.0"
    provider: str = ""
    quantum_signature: Optional[str] = None
    status: str = "initialized"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Cell':
        """Create a Cell from a dictionary."""
        return cls(**data)
    
    def update(self, **kwargs) -> 'Cell':
        """Update cell attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self


@dataclass
class Solution:
    """
    Represents an assembled solution of cells.
    
    A solution consists of a set of interconnected cells that together
    fulfill a specific user intent.
    
    Attributes:
        id: Unique identifier for this solution
        cells: Cells that make up this solution
        quantum_signature: Quantum-resistant signature for security
        created_at: Creation timestamp
        intent: Analyzed user intent
        status: Current status of the solution
        context: Context in which the solution was created
        connection_map: How cells are connected
        performance_metrics: Execution performance metrics
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cells: Dict[str, Cell] = field(default_factory=dict)
    quantum_signature: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    intent: Dict[str, Any] = field(default_factory=dict)
    status: str = "initializing"
    context: Dict[str, Any] = field(default_factory=dict)
    connection_map: Dict[str, List[str]] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def add_cell(self, cell: Cell) -> None:
        """Add a cell to the solution."""
        self.cells[cell.id] = cell
    
    def remove_cell(self, cell_id: str) -> bool:
        """Remove a cell from the solution."""
        if cell_id in self.cells:
            del self.cells[cell_id]
            return True
        return False
    
    def get_cell(self, cell_id: str) -> Optional[Cell]:
        """Get a cell by ID."""
        return self.cells.get(cell_id)
    
    def get_cells_by_capability(self, capability: str) -> List[Cell]:
        """Get all cells with a specific capability."""
        return [
            cell for cell in self.cells.values()
            if cell.capability == capability
        ]
    
    def update_status(self, new_status: str) -> None:
        """Update the solution status."""
        self.status = new_status
    
    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update performance metrics."""
        self.performance_metrics.update(metrics)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        # Convert Cell objects to dictionaries
        result["cells"] = {cell_id: cell.to_dict() for cell_id, cell in self.cells.items()}
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Solution':
        """Create a Solution from a dictionary."""
        # Convert cell dictionaries to Cell objects
        cells_dict = data.pop("cells", {})
        solution = cls(**data)
        solution.cells = {cell_id: Cell.from_dict(cell_data) for cell_id, cell_data in cells_dict.items()}
        return solution


@dataclass
class CellConfiguration:
    """
    Represents a configuration of cells that work together.
    
    A cell configuration defines a specific arrangement of cells that
    has been successful in fulfilling a particular type of intent.
    It can be used as a template for future assemblies.
    
    Attributes:
        id: Unique identifier for this configuration
        name: Descriptive name for the configuration
        cell_specs: Specifications for the cells in this configuration
        connection_map: How cells are connected
        capabilities: Capabilities provided by this configuration
        performance_score: Score indicating how well this configuration performs
        usage_count: Number of times this configuration has been used
        created_at: Creation timestamp
        last_used_at: Last time this configuration was used
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    cell_specs: List[Dict[str, Any]] = field(default_factory=list)
    connection_map: Dict[str, List[str]] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    performance_score: float = 0.0
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used_at: Optional[str] = None
    
    def add_cell_spec(self, cell_type: str, capability: str, version: str = "latest", 
                      parameters: Dict[str, Any] = None) -> None:
        """Add a cell specification to the configuration."""
        spec = {
            "cell_type": cell_type,
            "capability": capability,
            "version": version,
            "parameters": parameters or {}
        }
        self.cell_specs.append(spec)
    
    def update_performance(self, new_score: float) -> None:
        """Update the performance score."""
        # Calculate a weighted average
        total = self.performance_score * self.usage_count
        self.usage_count += 1
        self.performance_score = (total + new_score) / self.usage_count
        self.last_used_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CellConfiguration':
        """Create a CellConfiguration from a dictionary."""
        return cls(**data)


@dataclass
class QuantumSignature:
    """
    Represents a quantum-resistant cryptographic signature.
    
    Quantum signatures are used throughout the QCC system for security
    verification and to maintain the quantum trail of user interactions.
    
    Attributes:
        signature_id: Unique identifier for this signature
        value: The cryptographic signature value
        algorithm: Algorithm used to generate the signature
        created_at: Creation timestamp
        expiration: Expiration timestamp
        metadata: Additional metadata for the signature
    """
    signature_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    value: str = ""
    algorithm: str = "CRYSTALS-Dilithium"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expiration: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the signature has expired."""
        if not self.expiration:
            return False
        
        expiration_dt = datetime.fromisoformat(self.expiration)
        return datetime.now() > expiration_dt
    
    def verify(self, data: Any) -> bool:
        """
        Verify the signature against provided data.
        
        In a real implementation, this would use the actual
        verification algorithm. This is a placeholder.
        """
        # Placeholder for actual verification logic
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuantumSignature':
        """Create a QuantumSignature from a dictionary."""
        return cls(**data)


@dataclass
class AssemblyPattern:
    """
    Represents a pattern of cell assembly found in the quantum trail.
    
    Assembly patterns are used to identify common cell configurations
    that work well for particular intents, enabling the system to
    improve over time.
    
    Attributes:
        pattern_id: Unique identifier for this pattern
        capabilities: Capabilities associated with the pattern
        cell_types: Types of cells commonly used in this pattern
        connection_patterns: Common connection patterns
        success_rate: Rate of successful assemblies using this pattern
        average_performance: Average performance metrics
        usage_count: Number of times this pattern has been observed
        created_at: Creation timestamp
        last_observed_at: Last time this pattern was observed
    """
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capabilities: List[str] = field(default_factory=list)
    cell_types: List[str] = field(default_factory=list)
    connection_patterns: List[Dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    average_performance: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_observed_at: Optional[str] = None
    
    def update_with_assembly(self, assembly: Dict[str, Any], success: bool) -> None:
        """Update pattern with a new assembly observation."""
        self.usage_count += 1
        self.last_observed_at = datetime.now().isoformat()
        
        # Update success rate
        total_success = self.success_rate * (self.usage_count - 1)
        total_success += 1 if success else 0
        self.success_rate = total_success / self.usage_count
        
        # Update performance metrics
        performance = assembly.get("performance_metrics", {})
        for key, value in performance.items():
            if key in self.average_performance:
                self.average_performance[key] = (
                    (self.average_performance[key] * (self.usage_count - 1) + value) /
                    self.usage_count
                )
            else:
                self.average_performance[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AssemblyPattern':
        """Create an AssemblyPattern from a dictionary."""
        return cls(**data)


@dataclass
class CapabilitySpecification:
    """
    Represents the specification for a cell capability.
    
    Capability specifications define the inputs, outputs, and parameters
    for a specific capability, ensuring consistent interfaces across
    different cell implementations.
    
    Attributes:
        name: Name of the capability
        description: Human-readable description
        version: Specification version
        parameters: Defined parameters for this capability
        inputs: Expected inputs
        outputs: Produced outputs
        examples: Usage examples
    """
    name: str
    description: str = ""
    version: str = "1.0.0"
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate parameters against the specification.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            (Valid, Reason) tuple
        """
        # Check required parameters
        for param_spec in self.parameters:
            param_name = param_spec.get("name")
            required = param_spec.get("required", False)
            
            if required and (param_name not in parameters):
                return False, f"Missing required parameter: {param_name}"
            
            # Type checking
            if param_name in parameters:
                param_type = param_spec.get("type")
                param_value = parameters[param_name]
                
                # Skip type checking if type not specified
                if not param_type:
                    continue
                
                # Basic type checking
                if param_type == "string" and not isinstance(param_value, str):
                    return False, f"Parameter {param_name} should be a string"
                elif param_type == "number" and not isinstance(param_value, (int, float)):
                    return False, f"Parameter {param_name} should be a number"
                elif param_type == "boolean" and not isinstance(param_value, bool):
                    return False, f"Parameter {param_name} should be a boolean"
                elif param_type == "array" and not isinstance(param_value, list):
                    return False, f"Parameter {param_name} should be an array"
                elif param_type == "object" and not isinstance(param_value, dict):
                    return False, f"Parameter {param_name} should be an object"
        
        return True, ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CapabilitySpecification':
        """Create a CapabilitySpecification from a dictionary."""
        return cls(**data)

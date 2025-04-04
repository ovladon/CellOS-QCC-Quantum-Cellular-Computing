"""
Cell configuration model for the QCC Assembler.

This module defines the CellConfiguration class, which represents a
specific arrangement of cells that has been used successfully in the past.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class CellConfiguration:
    """
    Represents a specific configuration of cells.
    
    A cell configuration stores information about a set of cells that
    have been successfully used together, along with their connection
    patterns and performance metrics.
    
    Attributes:
        id (str): Unique identifier for this configuration
        cell_specs (List[Dict[str, Any]]): Specifications for the cells in this configuration
        """
Cell configuration model for the QCC Assembler.

This module defines the CellConfiguration class, which represents a
specific arrangement of cells that has been used successfully in the past.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class CellConfiguration:
    """
    Represents a specific configuration of cells.
    
    A cell configuration stores information about a set of cells that
    have been successfully used together, along with their connection
    patterns and performance metrics.
    
    Attributes:
        id (str): Unique identifier for this configuration
        cell_specs (List[Dict[str, Any]]): Specifications for the cells in this configuration
        connection_map (Dict[str, List[str]]): How cells are connected
        performance_score (float): Score indicating how well this configuration performed
        created_at (str): ISO timestamp of when the configuration was created
        last_used_at (str): ISO timestamp of when the configuration was last used
        use_count (int): Number of times this configuration has been used
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        cell_specs: Optional[List[Dict[str, Any]]] = None,
        connection_map: Optional[Dict[str, List[str]]] = None,
        performance_score: float = 0.0,
        created_at: Optional[str] = None,
        last_used_at: Optional[str] = None,
        use_count: int = 0
    ):
        """
        Initialize a cell configuration.
        
        Args:
            id: Unique identifier (generated if not provided)
            cell_specs: Specifications for the cells in this configuration
            connection_map: How cells are connected
            performance_score: Score indicating how well this configuration performed
            created_at: Creation timestamp (current time if not provided)
            last_used_at: Last usage timestamp (current time if not provided)
            use_count: Number of times this configuration has been used
        """
        self.id = id or str(uuid.uuid4())
        self.cell_specs = cell_specs or []
        self.connection_map = connection_map or {}
        self.performance_score = performance_score
        self.created_at = created_at or datetime.now().isoformat()
        self.last_used_at = last_used_at or self.created_at
        self.use_count = use_count
        
    def record_usage(self, performance_metrics: Dict[str, Any]) -> None:
        """
        Record a usage of this configuration.
        
        Args:
            performance_metrics: Metrics from the solution using this configuration
        """
        self.use_count += 1
        self.last_used_at = datetime.now().isoformat()
        
        # Update performance score (weighted average)
        if self.use_count > 1:
            # Calculate new score based on metrics
            new_score = self._calculate_score(performance_metrics)
            
            # Weight by number of uses, giving more weight to recent results
            self.performance_score = (
                (self.performance_score * (self.use_count - 1) * 0.8) + 
                (new_score * 0.2 * self.use_count)
            ) / self.use_count
        else:
            # First usage, just set the score
            self.performance_score = self._calculate_score(performance_metrics)
            
    def _calculate_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate a performance score from metrics.
        
        Args:
            metrics: Performance metrics
            
        Returns:
            Calculated performance score
        """
        # Simple example scoring function
        # In a real implementation, this would be more sophisticated
        score = 100.0  # Start with perfect score
        
        # Penalize for long assembly time
        assembly_time_ms = metrics.get("assembly_time_ms", 0)
        if assembly_time_ms > 0:
            score -= min(20, assembly_time_ms / 50)  # Max 20 point penalty
            
        # Penalize for high resource usage
        memory_peak_mb = metrics.get("memory_peak_mb", 0)
        if memory_peak_mb > 0:
            score -= min(10, memory_peak_mb / 100)  # Max 10 point penalty
            
        cpu_usage_avg = metrics.get("cpu_usage_avg", 0)
        if cpu_usage_avg > 0:
            score -= min(10, cpu_usage_avg / 10)  # Max 10 point penalty
            
        # Bonus for fast total usage time (if under 5 seconds)
        total_usage_time_ms = metrics.get("total_usage_time_ms", 0)
        if 0 < total_usage_time_ms < 5000:
            score += min(10, (5000 - total_usage_time_ms) / 500)  # Max 10 point bonus
            
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary representation.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "id": self.id,
            "cell_specs": self.cell_specs,
            "connection_map": self.connection_map,
            "performance_score": self.performance_score,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "use_count": self.use_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CellConfiguration':
        """
        Create a configuration from a dictionary representation.
        
        Args:
            data: Dictionary representation of a configuration
            
        Returns:
            CellConfiguration object
        """
        return cls(
            id=data.get("id"),
            cell_specs=data.get("cell_specs", []),
            connection_map=data.get("connection_map", {}),
            performance_score=data.get("performance_score", 0.0),
            created_at=data.get("created_at"),
            last_used_at=data.get("last_used_at"),
            use_count=data.get("use_count", 0)
        )

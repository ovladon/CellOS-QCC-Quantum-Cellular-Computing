"""
Transaction definition for the Quantum Trail blockchain.

This module defines the Transaction class, which represents a single
transaction in the blockchain, containing data about cell assemblies
and their performance.
"""

import time
import json
from typing import Dict, List, Any, Optional
import uuid

from .crypto import create_quantum_signature, verify_quantum_signature, hash_data


class Transaction:
    """
    Represents a transaction in the Quantum Trail blockchain.
    
    Each transaction contains data about a cell assembly, performance metrics,
    and a quantum-resistant signature for verification.
    
    Attributes:
        id (str): Unique transaction identifier
        timestamp (float): Unix timestamp of transaction creation
        quantum_signature (str): Quantum-resistant signature of the sender
        solution_id (str): Identifier for the cell assembly solution
        cell_ids (List[str]): List of cells in the assembly
        connection_map (Dict[str, List[str]]): How cells are connected
        performance_metrics (Dict[str, Any]): Solution performance metrics
        signature (str): Digital signature of the transaction
    """
    
    def __init__(
        self,
        quantum_signature: str,
        solution_id: str,
        cell_ids: List[str],
        connection_map: Dict[str, List[str]],
        performance_metrics: Dict[str, Any],
        id: Optional[str] = None,
        timestamp: Optional[float] = None,
        signature: Optional[str] = None
    ):
        """
        Initialize a new transaction.
        
        Args:
            quantum_signature: Anonymous signature of the user
            solution_id: Identifier for the cell assembly solution
            cell_ids: List of cells in the assembly
            connection_map: How cells are connected
            performance_metrics: Solution performance metrics
            id: Unique transaction identifier (generated if not provided)
            timestamp: Unix timestamp (defaults to current time)
            signature: Digital signature (generated from data if not provided)
        """
        self.id = id or str(uuid.uuid4())
        self.timestamp = timestamp or time.time()
        self.quantum_signature = quantum_signature
        self.solution_id = solution_id
        self.cell_ids = cell_ids
        self.connection_map = connection_map
        self.performance_metrics = performance_metrics
        
        # Generate signature if not provided
        self.signature = signature or self._generate_signature()
    
    def _generate_signature(self) -> str:
        """
        Generate a digital signature for this transaction.
        
        Returns:
            Digital signature
        """
        # In a real implementation, this would use a private key
        # For the QCC system, this uses quantum-resistant signatures
        data = {
            "id": self.id,
            "timestamp": self.timestamp,
            "quantum_signature": self.quantum_signature,
            "solution_id": self.solution_id,
            "cell_ids": self.cell_ids,
            "connection_map": self.connection_map,
            "performance_metrics": self.performance_metrics
        }
        
        # Use quantum-resistant signing (this is a placeholder)
        # In a real implementation, this would use the actual private key
        return create_quantum_signature(data, "private_key_placeholder")
    
    def is_valid(self) -> bool:
        """
        Validate the transaction.
        
        Returns:
            True if the transaction is valid
        """
        # Verify that the transaction has a valid structure
        if not self.id or not self.quantum_signature or not self.solution_id:
            return False
        
        # Verify the signature
        data = {
            "id": self.id,
            "timestamp": self.timestamp,
            "quantum_signature": self.quantum_signature,
            "solution_id": self.solution_id,
            "cell_ids": self.cell_ids,
            "connection_map": self.connection_map,
            "performance_metrics": self.performance_metrics
        }
        
        # Use quantum-resistant verification (this is a placeholder)
        # In a real implementation, this would use the actual public key
        return verify_quantum_signature(data, self.signature, "public_key_placeholder")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction to a dictionary.
        
        Returns:
            Dictionary representation of the transaction
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "quantum_signature": self.quantum_signature,
            "solution_id": self.solution_id,
            "cell_ids": self.cell_ids,
            "connection_map": self.connection_map,
            "performance_metrics": self.performance_metrics,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """
        Create a transaction from a dictionary.
        
        Args:
            data: Dictionary representation of a transaction
        
        Returns:
            Transaction object
        """
        return cls(
            quantum_signature=data.get("quantum_signature", ""),
            solution_id=data.get("solution_id", ""),
            cell_ids=data.get("cell_ids", []),
            connection_map=data.get("connection_map", {}),
            performance_metrics=data.get("performance_metrics", {}),
            id=data.get("id"),
            timestamp=data.get("timestamp"),
            signature=data.get("signature")
        )

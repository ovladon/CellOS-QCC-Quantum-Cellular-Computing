"""
Signature Generator for Quantum Trail

This module implements the signature generation functionality for the quantum trail system,
creating unforgeable quantum-resistant signatures that uniquely identify cell assemblies.
"""

import os
import time
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Union, Tuple

from .algorithms import (
    DilithiumSigner,
    SPHINCSPlusSigner,
    HybridSigner,
    SignatureAlgorithm
)
from .utils import (
    encode_signature,
    hash_data,
    generate_nonce
)

logger = logging.getLogger(__name__)

class SignatureGenerator:
    """
    Generator for quantum-resistant signatures in the quantum trail system.
    
    This class handles the creation of unique, unforgeable signatures for cell assemblies,
    using post-quantum cryptographic algorithms to ensure security against quantum attacks.
    """
    
    def __init__(self, algorithm: str = "hybrid", key_path: Optional[str] = None):
        """
        Initialize the signature generator.
        
        Args:
            algorithm: Signature algorithm to use ("dilithium", "sphincs+", or "hybrid")
            key_path: Optional path to load cryptographic keys from
        """
        self.algorithm = algorithm.lower()
        
        # Initialize the appropriate signer based on algorithm
        if self.algorithm == "dilithium":
            self.signer = DilithiumSigner(key_path)
        elif self.algorithm == "sphincs+":
            self.signer = SPHINCSPlusSigner(key_path)
        elif self.algorithm == "hybrid":
            self.signer = HybridSigner(key_path)
        else:
            raise ValueError(f"Unsupported signature algorithm: {algorithm}")
        
        logger.info(f"Initialized SignatureGenerator with algorithm: {algorithm}")
    
    async def generate_signature(self, user_id: str, assembly_data: Dict[str, Any], 
                                context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a quantum-resistant signature for a cell assembly.
        
        Args:
            user_id: Anonymous identifier for the user
            assembly_data: Data about the cell assembly to sign
            context: Additional context information
            
        Returns:
            Encoded signature string
        """
        # Create signature payload
        timestamp = time.time()
        nonce = generate_nonce()
        
        payload = {
            "timestamp": timestamp,
            "nonce": nonce,
            "user_id_hash": hash_data(user_id),  # Hash user ID for privacy
            "assembly_hash": hash_data(assembly_data),
            "context_hash": hash_data(context) if context else None,
            "signature_id": str(uuid.uuid4())
        }
        
        # Sign the payload using the selected algorithm
        try:
            signature_data = await self.signer.sign(payload)
            
            # Encode the signature and payload together
            encoded_signature = encode_signature(signature_data, payload)
            
            logger.debug(f"Generated signature: {payload['signature_id']}")
            return encoded_signature
            
        except Exception as e:
            logger.error(f"Signature generation failed: {str(e)}")
            raise
    
    async def generate_assembly_signature(self, user_id: str, 
                                         capabilities: List[str],
                                         cells: List[Dict[str, Any]],
                                         connections: Dict[str, List[str]],
                                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a signature specifically for a cell assembly.
        
        This method creates a structured representation of the assembly before signing.
        
        Args:
            user_id: Anonymous identifier for the user
            capabilities: List of capabilities required by the assembly
            cells: List of cells in the assembly
            connections: Connection map between cells
            context: Additional context information
            
        Returns:
            Encoded signature string
        """
        # Create assembly data structure
        assembly_data = {
            "capabilities": sorted(capabilities),
            "cell_count": len(cells),
            "cell_ids": [cell.get("id") for cell in cells],
            "cell_types": [cell.get("type") for cell in cells],
            "connection_map": connections,
            "assembly_time": time.time()
        }
        
        # Generate signature
        return await self.generate_signature(user_id, assembly_data, context)
    
    async def generate_solution_signature(self, user_id: str, solution_data: Dict[str, Any],
                                        context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a signature for a complete solution.
        
        Args:
            user_id: Anonymous identifier for the user
            solution_data: Data about the solution
            context: Additional context information
            
        Returns:
            Encoded signature string
        """
        # Extract essential solution data to sign
        essential_data = {
            "id": solution_data.get("id"),
            "cells": [cell.get("id") for cell in solution_data.get("cells", {}).values()],
            "intent": solution_data.get("intent", {}).get("required_capabilities", []),
            "created_at": solution_data.get("created_at")
        }
        
        # Generate signature
        return await self.generate_signature(user_id, essential_data, context)
    
    def rotate_keys(self) -> None:
        """
        Rotate the cryptographic keys used for signature generation.
        
        This is a security best practice to limit the impact of potential key compromise.
        """
        logger.info(f"Rotating keys for {self.algorithm} signer")
        self.signer.rotate_keys()
    
    async def get_public_parameters(self) -> Dict[str, Any]:
        """
        Get the public parameters of the signature algorithm.
        
        Returns:
            Dictionary of public parameters
        """
        return await self.signer.get_public_parameters()
    
    def save_keys(self, key_path: str) -> None:
        """
        Save the current keys to the specified path.
        
        Args:
            key_path: Path to save keys to
        """
        self.signer.save_keys(key_path)

"""
Security Manager implementation for the QCC Assembler.

This module provides the SecurityManager class, which coordinates
security-related operations within the QCC system.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set

from qcc.common.exceptions import SecurityVerificationError
from qcc.common.models import Cell

from .signature_verifier import SignatureVerifier
from .cell_verifier import CellVerifier
from .permission_manager import PermissionManager

logger = logging.getLogger(__name__)

class SecurityManager:
    """
    Manages security operations for the QCC Assembler.
    
    The SecurityManager coordinates security verification, permission
    management, and other security-related operations.
    
    Attributes:
        signature_verifier (SignatureVerifier): Verifies quantum signatures
        cell_verifier (CellVerifier): Verifies cell security properties
        permission_manager (PermissionManager): Manages access permissions
        security_level (str): Current security level (standard, high, maximum)
    """
    
    def __init__(self, security_level: str = "standard"):
        """
        Initialize the security manager.
        
        Args:
            security_level: Security level (standard, high, maximum)
        """
        self.signature_verifier = SignatureVerifier()
        self.cell_verifier = CellVerifier()
        self.permission_manager = PermissionManager()
        self.security_level = security_level
        
        logger.info(f"Security manager initialized with level: {security_level}")
        
    async def verify_cells(
        self, 
        cells: Dict[str, Cell], 
        quantum_signature: str
    ) -> bool:
        """
        Verify security properties of a set of cells.
        
        Args:
            cells: Dictionary of cells to verify
            quantum_signature: Quantum signature for verification
            
        Returns:
            True if verification passes
            
        Raises:
            SecurityVerificationError: If verification fails
        """
        logger.info(f"Verifying {len(cells)} cells")
        
        # Verify the quantum signature
        if not await self.signature_verifier.verify_signature(quantum_signature):
            raise SecurityVerificationError("Invalid quantum signature")
            
        # Verify each cell
        verification_results = []
        for cell_id, cell in cells.items():
            try:
                verified = await self.cell_verifier.verify_cell(
                    cell, 
                    quantum_signature, 
                    security_level=self.security_level
                )
                verification_results.append(verified)
                
                if verified:
                    logger.debug(f"Cell verified: {cell_id}")
                else:
                    logger.warning(f"Cell verification failed: {cell_id}")
                    raise SecurityVerificationError(f"Verification failed for cell: {cell_id}")
                    
            except Exception as e:
                logger.error(f"Error verifying cell {cell_id}: {e}")
                raise SecurityVerificationError(f"Error verifying cell {cell_id}: {str(e)}")
                
        # All cells must be verified
        if all(verification_results):
            logger.info(f"All {len(cells)} cells successfully verified")
            return True
        else:
            failed_count = verification_results.count(False)
            raise SecurityVerificationError(f"{failed_count} cells failed verification")
            
    async def generate_permissions(
        self, 
        cells: Dict[str, Cell],
        capabilities: List[str],
        quantum_signature: str
    ) -> Dict[str, Any]:
        """
        Generate permission sets for cells.
        
        Args:
            cells: Dictionary of cells
            capabilities: Required capabilities
            quantum_signature: Quantum signature
            
        Returns:
            Dictionary mapping cell IDs to permission sets
        """
        logger.info(f"Generating permissions for {len(cells)} cells")
        
        permissions = {}
        for cell_id, cell in cells.items():
            cell_permissions = await self.permission_manager.generate_cell_permissions(
                cell, 
                capabilities, 
                quantum_signature,
                security_level=self.security_level
            )
            permissions[cell_id] = cell_permissions
            logger.debug(f"Generated permissions for cell {cell_id}")
            
        return permissions
    
    async def verify_connection(
        self, 
        source_cell: Cell, 
        target_cell: Cell,
        quantum_signature: str
    ) -> bool:
        """
        Verify that a connection between cells is allowed.
        
        Args:
            source_cell: Source cell for the connection
            target_cell: Target cell for the connection
            quantum_signature: Quantum signature
            
        Returns:
            True if connection is allowed
            
        Raises:
            SecurityVerificationError: If connection is not allowed
        """
        logger.info(f"Verifying connection from {source_cell.id} to {target_cell.id}")
        
        # Check if connection is allowed based on security level
        allowed = await self.permission_manager.check_connection_permission(
            source_cell,
            target_cell,
            quantum_signature,
            security_level=self.security_level
        )
        
        if allowed:
            logger.debug(f"Connection allowed: {source_cell.id} -> {target_cell.id}")
            return True
        else:
            logger.warning(f"Connection denied: {source_cell.id} -> {target_cell.id}")
            raise SecurityVerificationError(
                f"Security policy denies connection from {source_cell.id} to {target_cell.id}"
            )
            
    def set_security_level(self, level: str) -> None:
        """
        Set the security level for the manager.
        
        Args:
            level: Security level (standard, high, maximum)
            
        Raises:
            ValueError: If level is invalid
        """
        valid_levels = ["standard", "high", "maximum"]
        if level not in valid_levels:
            raise ValueError(f"Invalid security level: {level}. Must be one of {valid_levels}")
            
        self.security_level = level
        logger.info(f"Security level set to: {level}")

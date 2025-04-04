"""
Main cell verification module for the QCC provider system.

This module orchestrates the verification of cells through a series of checks:
- Signature validation
- Security scanning
- Compatibility checking
- Permission validation

Cells must pass all verification stages before they can be registered
with a provider and distributed to assemblers.
"""

import logging
import time
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple, Set, Union

from .signature import SignatureValidator
from .security_scanner import SecurityScanner
from .compatibility import CompatibilityChecker
from .permissions import PermissionValidator
from .exceptions import (
    VerificationError,
    SignatureVerificationError,
    SecurityViolationError,
    CompatibilityError,
    PermissionError
)

from qcc.common.models import Cell, CellManifest, VerificationResult
from qcc.common.config import VerificationConfig

logger = logging.getLogger(__name__)

class CellVerifier:
    """
    Comprehensive verifier for QCC cells.
    
    Coordinates multiple verification steps to ensure cells meet all
    requirements before they can be registered, distributed, and used
    in the QCC ecosystem.
    """
    
    def __init__(self, config: Optional[VerificationConfig] = None):
        """
        Initialize the cell verifier with optional configuration.
        
        Args:
            config: Verification configuration options
        """
        self.config = config or VerificationConfig()
        
        # Initialize sub-verifiers
        self.signature_validator = SignatureValidator(self.config)
        self.security_scanner = SecurityScanner(self.config)
        self.compatibility_checker = CompatibilityChecker(self.config)
        self.permission_validator = PermissionValidator(self.config)
        
        # Track verification results
        self.verification_results = {}
        
        logger.info("Cell verifier initialized with verification level: %s", 
                   self.config.verification_level)
    
    async def verify_cell(self, cell: Cell) -> VerificationResult:
        """
        Perform comprehensive verification of a cell.
        
        Args:
            cell: The cell to verify
            
        Returns:
            VerificationResult object with verification details
            
        Raises:
            VerificationError: If verification fails
        """
        cell_id = cell.id
        start_time = time.time()
        
        logger.info("Starting verification of cell %s", cell_id)
        
        # Create verification result object
        result = VerificationResult(
            cell_id=cell_id,
            verified=False,
            timestamp=time.time(),
            verification_level=self.config.verification_level,
            verification_details={}
        )
        
        try:
            # Step 1: Validate signature
            signature_result = await self.signature_validator.validate(cell)
            result.verification_details["signature"] = signature_result
            
            if not signature_result["passed"]:
                raise SignatureVerificationError(
                    f"Signature verification failed: {signature_result['message']}"
                )
            
            # Step 2: Security scanning
            security_result = await self.security_scanner.scan(cell)
            result.verification_details["security"] = security_result
            
            if not security_result["passed"]:
                raise SecurityViolationError(
                    f"Security scan failed: {security_result['message']}"
                )
            
            # Step 3: Compatibility checking
            compatibility_result = await self.compatibility_checker.check(cell)
            result.verification_details["compatibility"] = compatibility_result
            
            if not compatibility_result["passed"]:
                raise CompatibilityError(
                    f"Compatibility check failed: {compatibility_result['message']}"
                )
            
            # Step 4: Permission validation
            permission_result = await self.permission_validator.validate(cell)
            result.verification_details["permissions"] = permission_result
            
            if not permission_result["passed"]:
                raise PermissionError(
                    f"Permission validation failed: {permission_result['message']}"
                )
            
            # All verifications passed
            result.verified = True
            result.verification_time = time.time() - start_time
            
            # Generate verification hash
            result.verification_hash = self._generate_verification_hash(result)
            
            # Store result
            self.verification_results[cell_id] = result
            
            logger.info("Cell %s successfully verified in %.2f seconds", 
                      cell_id, result.verification_time)
            
            return result
            
        except (SignatureVerificationError, SecurityViolationError,
                CompatibilityError, PermissionError) as e:
            logger.error("Cell %s verification failed: %s", cell_id, str(e))
            
            result.verified = False
            result.verification_time = time.time() - start_time
            result.error_message = str(e)
            
            # Store failed result
            self.verification_results[cell_id] = result
            
            raise VerificationError(str(e)) from e
        
        except Exception as e:
            logger.exception("Unexpected error during verification of cell %s: %s", 
                           cell_id, str(e))
            
            result.verified = False
            result.verification_time = time.time() - start_time
            result.error_message = f"Unexpected verification error: {str(e)}"
            
            # Store failed result
            self.verification_results[cell_id] = result
            
            raise VerificationError(f"Unexpected verification error: {str(e)}") from e
    
    async def verify_cell_batch(self, cells: List[Cell]) -> Dict[str, VerificationResult]:
        """
        Verify a batch of cells.
        
        Args:
            cells: List of cells to verify
            
        Returns:
            Dictionary mapping cell IDs to verification results
        """
        results = {}
        
        for cell in cells:
            try:
                result = await self.verify_cell(cell)
                results[cell.id] = result
            except VerificationError as e:
                # Continue verifying the rest of the cells even if one fails
                logger.warning("Cell %s verification failed in batch: %s", 
                              cell.id, str(e))
                
                # Include the failed result
                if cell.id in self.verification_results:
                    results[cell.id] = self.verification_results[cell.id]
        
        return results
    
    async def reverify_cell(self, cell: Cell) -> VerificationResult:
        """
        Re-verify a previously verified cell.
        
        This is useful for periodic re-verification of cells to ensure they
        still meet security requirements, especially after security policy updates.
        
        Args:
            cell: The cell to re-verify
            
        Returns:
            Updated verification result
        """
        # Clear previous verification result
        if cell.id in self.verification_results:
            del self.verification_results[cell.id]
        
        # Perform full verification
        return await self.verify_cell(cell)
    
    def get_verification_result(self, cell_id: str) -> Optional[VerificationResult]:
        """
        Get the verification result for a specific cell.
        
        Args:
            cell_id: ID of the cell
            
        Returns:
            VerificationResult if available, None otherwise
        """
        return self.verification_results.get(cell_id)
    
    def _generate_verification_hash(self, result: VerificationResult) -> str:
        """
        Generate a hash of the verification result for integrity verification.
        
        Args:
            result: Verification result to hash
            
        Returns:
            Hash string
        """
        # Create a deterministic JSON representation
        verification_data = {
            "cell_id": result.cell_id,
            "verified": result.verified,
            "timestamp": result.timestamp,
            "verification_level": result.verification_level,
            "verification_details": result.verification_details
        }
        
        serialized = json.dumps(verification_data, sort_keys=True)
        
        # Generate hash
        hash_obj = hashlib.sha256(serialized.encode())
        return hash_obj.hexdigest()

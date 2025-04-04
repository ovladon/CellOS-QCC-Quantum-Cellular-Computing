"""
Signature Verifier for Quantum Trail

This module implements the signature verification functionality for the quantum trail system,
ensuring the authenticity and integrity of quantum-resistant signatures.
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Union, Tuple, List

from .algorithms import (
    DilithiumSigner,
    SPHINCSPlusSigner,
    HybridSigner,
    SignatureAlgorithm
)
from .utils import (
    decode_signature,
    hash_data,
    verify_integrity
)

logger = logging.getLogger(__name__)

class SignatureVerifier:
    """
    Verifier for quantum-resistant signatures in the quantum trail system.
    
    This class handles the verification of signatures to ensure their authenticity
    and integrity, using post-quantum cryptographic algorithms.
    """
    
    def __init__(self, public_params_path: Optional[str] = None):
        """
        Initialize the signature verifier.
        
        Args:
            public_params_path: Optional path to load public parameters from
        """
        # Initialize signers for each algorithm type
        self.signers = {
            "dilithium": DilithiumSigner(public_only=True, key_path=public_params_path),
            "sphincs+": SPHINCSPlusSigner(public_only=True, key_path=public_params_path),
            "hybrid": HybridSigner(public_only=True, key_path=public_params_path)
        }
        
        logger.info("Initialized SignatureVerifier")
    
    async def verify_signature(self, encoded_signature: str, 
                              expected_user_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a quantum-resistant signature.
        
        Args:
            encoded_signature: The encoded signature string to verify
            expected_user_id: Optional user ID to verify against
            
        Returns:
            Tuple containing:
            - Boolean indicating verification success
            - Payload data from the signature
        """
        try:
            # Decode the signature
            signature_data, payload = decode_signature(encoded_signature)
            
            # Get the algorithm from the signature metadata
            algorithm = signature_data.get("algorithm", "hybrid").lower()
            
            # Verify if we have a specific user ID to check
            if expected_user_id:
                expected_hash = hash_data(expected_user_id)
                if payload.get("user_id_hash") != expected_hash:
                    logger.warning(f"User ID hash mismatch for signature: {payload.get('signature_id')}")
                    return False, payload
            
            # Get the appropriate signer for the algorithm
            if algorithm not in self.signers:
                logger.error(f"Unsupported signature algorithm: {algorithm}")
                return False, payload
            
            signer = self.signers[algorithm]
            
            # Verify the signature
            verification_result = await signer.verify(signature_data, payload)
            
            if verification_result:
                logger.debug(f"Signature verified successfully: {payload.get('signature_id')}")
            else:
                logger.warning(f"Signature verification failed: {payload.get('signature_id')}")
            
            return verification_result, payload
            
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False, {}
    
    async def verify_assembly_signature(self, encoded_signature: str, 
                                      expected_capabilities: Optional[List[str]] = None,
                                      expected_cell_count: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a signature for a cell assembly with additional assembly-specific checks.
        
        Args:
            encoded_signature: The encoded signature string to verify
            expected_capabilities: Optional list of capabilities to verify against
            expected_cell_count: Optional expected number of cells
            
        Returns:
            Tuple containing:
            - Boolean indicating verification success
            - Payload data from the signature
        """
        # First perform basic signature verification
        is_valid, payload = await self.verify_signature(encoded_signature)
        
        if not is_valid:
            return False, payload
        
        # Decode the full payload to access assembly data
        try:
            signature_data, payload = decode_signature(encoded_signature)
            assembly_hash = payload.get("assembly_hash")
            
            # Verify if we have expected capabilities to check
            if expected_capabilities and "assembly_data" in payload:
                assembly_data = payload["assembly_data"]
                if "capabilities" in assembly_data:
                    stored_capabilities = set(assembly_data["capabilities"])
                    expected_capabilities_set = set(expected_capabilities)
                    
                    if not expected_capabilities_set.issubset(stored_capabilities):
                        logger.warning(f"Capabilities mismatch for signature: {payload.get('signature_id')}")
                        return False, payload
            
            # Verify if we have expected cell count to check
            if expected_cell_count is not None and "assembly_data" in payload:
                assembly_data = payload["assembly_data"]
                if "cell_count" in assembly_data and assembly_data["cell_count"] != expected_cell_count:
                    logger.warning(f"Cell count mismatch for signature: {payload.get('signature_id')}")
                    return False, payload
            
            return True, payload
            
        except Exception as e:
            logger.error(f"Assembly signature verification error: {str(e)}")
            return False, payload
    
    async def load_public_parameters(self, params_or_path: Union[Dict[str, Any], str]) -> None:
        """
        Load public parameters for signature verification.
        
        Args:
            params_or_path: Either a dictionary of parameters or a path to load from
        """
        if isinstance(params_or_path, str):
            # Load parameters from file
            with open(params_or_path, 'r') as f:
                params = json.load(f)
        else:
            params = params_or_path
        
        # Update each signer with the corresponding parameters
        for algorithm, signer in self.signers.items():
            if algorithm in params:
                signer.load_public_parameters(params[algorithm])
        
        logger.info("Loaded public parameters for signature verification")
    
    async def check_signature_freshness(self, encoded_signature: str, max_age_seconds: int = 86400) -> bool:
        """
        Check if a signature is within the acceptable age range.
        
        Args:
            encoded_signature: The encoded signature string to check
            max_age_seconds: Maximum acceptable age in seconds (default: 24 hours)
            
        Returns:
            Boolean indicating if the signature is fresh
        """
        try:
            # Decode the signature
            _, payload = decode_signature(encoded_signature)
            
            # Get the timestamp from the payload
            timestamp = payload.get("timestamp", 0)
            current_time = time.time()
            
            # Check if the signature is too old
            if current_time - timestamp > max_age_seconds:
                logger.warning(f"Signature too old: {payload.get('signature_id')}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Signature freshness check error: {str(e)}")
            return False

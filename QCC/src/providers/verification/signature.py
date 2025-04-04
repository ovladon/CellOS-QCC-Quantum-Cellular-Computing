"""
Cell signature validation module for QCC providers.

This module verifies the cryptographic signatures of cells to ensure they
come from trusted sources and haven't been tampered with. It supports both
classical and post-quantum cryptographic algorithms.
"""

import logging
import time
import os
from typing import Dict, Any, Optional
import json

import hashlib
import base64

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

from qcc.common.models import Cell, CellManifest
from qcc.common.config import VerificationConfig
from qcc.quantum_trail.signature import QuantumSignatureVerifier

from .exceptions import SignatureVerificationError

logger = logging.getLogger(__name__)

class SignatureValidator:
    """
    Validates cell signatures to ensure authenticity and integrity.
    
    Supports multiple signature schemes including:
    - Classical (RSA, ECDSA)
    - Post-quantum (CRYSTALS-Dilithium, SPHINCS+)
    - Hybrid approaches
    
    Verification includes both signature validation and integrity checking
    of the cell contents against the signed manifest.
    """
    
    def __init__(self, config: VerificationConfig):
        """
        Initialize the signature validator.
        
        Args:
            config: Verification configuration
        """
        self.config = config
        self.quantum_verifier = QuantumSignatureVerifier()
        
        # Load trusted keys from secure storage
        self._load_trusted_keys()
        
        logger.info("Signature validator initialized with %d trusted keys", 
                   len(self.trusted_keys))
    
    async def validate(self, cell: Cell) -> Dict[str, Any]:
        """
        Validate the signature and integrity of a cell.
        
        Args:
            cell: The cell to validate
            
        Returns:
            Validation result dictionary
        """
        start_time = time.time()
        
        # Default result structure
        result = {
            "passed": False,
            "message": "",
            "signature_type": "",
            "signer_id": "",
            "timestamp": time.time(),
            "integrity_verified": False,
            "validation_time_ms": 0
        }
        
        try:
            # Extract signature information from cell
            signature_info = self._extract_signature_info(cell)
            result["signature_type"] = signature_info["type"]
            result["signer_id"] = signature_info["signer_id"]
            
            # Verify the signature based on its type
            if signature_info["type"] == "quantum":
                # Use quantum signature verification
                signature_valid = await self._verify_quantum_signature(
                    cell, signature_info["signature"], signature_info["signer_id"]
                )
            elif signature_info["type"] in ["rsa", "ecdsa"]:
                # Use classical signature verification
                signature_valid = self._verify_classical_signature(
                    cell, signature_info["signature"], signature_info["signer_id"], 
                    signature_info["type"]
                )
            elif signature_info["type"] == "hybrid":
                # Verify both classical and quantum signatures
                signature_valid = await self._verify_hybrid_signature(
                    cell, signature_info["signature"], signature_info["signer_id"]
                )
            else:
                raise SignatureVerificationError(f"Unsupported signature type: {signature_info['type']}")
            
            if not signature_valid:
                result["message"] = "Signature verification failed"
                return result
            
            # Verify cell integrity by checking content against the manifest
            integrity_verified = self._verify_cell_integrity(cell)
            result["integrity_verified"] = integrity_verified
            
            if not integrity_verified:
                result["message"] = "Cell integrity check failed"
                return result
            
            # All checks passed
            result["passed"] = True
            result["message"] = "Signature and integrity verified successfully"
            
        except Exception as e:
            result["message"] = f"Signature validation error: {str(e)}"
            logger.error("Signature validation failed for cell %s: %s", 
                        cell.id, str(e))
        
        # Calculate validation time
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result
    
    def _extract_signature_info(self, cell: Cell) -> Dict[str, Any]:
        """
        Extract signature information from a cell.
        
        Args:
            cell: The cell to extract signature from
            
        Returns:
            Dictionary containing signature information
            
        Raises:
            SignatureVerificationError: If signature information is missing
        """
        if not hasattr(cell, 'manifest') or not cell.manifest:
            raise SignatureVerificationError("Cell manifest is missing")
        
        manifest = cell.manifest
        
        if not hasattr(manifest, 'signature') or not manifest.signature:
            raise SignatureVerificationError("Signature is missing from manifest")
        
        signature_data = manifest.signature
        
        # Validate required signature fields
        required_fields = ["type", "signer_id", "signature", "timestamp"]
        for field in required_fields:
            if field not in signature_data:
                raise SignatureVerificationError(f"Missing signature field: {field}")
        
        # Check signature timestamp for freshness if required
        if self.config.check_signature_freshness:
            max_age = self.config.max_signature_age_days * 24 * 3600
            if (time.time() - signature_data["timestamp"]) > max_age:
                raise SignatureVerificationError("Signature has expired")
        
        return signature_data
    
    async def _verify_quantum_signature(self, cell: Cell, signature: str, signer_id: str) -> bool:
        """
        Verify a quantum-resistant signature.
        
        Args:
            cell: The cell being verified
            signature: The signature string
            signer_id: ID of the signer
            
        Returns:
            True if valid, False otherwise
        """
        # Get the public key for this signer
        public_key = self._get_trusted_key(signer_id, "quantum")
        if not public_key:
            logger.warning("No trusted quantum key found for signer %s", signer_id)
            return False
        
        # Prepare the data that was signed (manifest without signature)
        signed_data = self._get_manifest_for_verification(cell)
        
        # Verify using quantum signature verifier
        try:
            return await self.quantum_verifier.verify(
                data=signed_data,
                signature=signature,
                public_key=public_key
            )
        except Exception as e:
            logger.error("Quantum signature verification error: %s", str(e))
            return False
    
    def _verify_classical_signature(self, cell: Cell, signature: str, signer_id: str,
                                   algorithm: str) -> bool:
        """
        Verify a classical cryptographic signature.
        
        Args:
            cell: The cell being verified
            signature: The signature string
            signer_id: ID of the signer
            algorithm: Signature algorithm ("rsa" or "ecdsa")
            
        Returns:
            True if valid, False otherwise
        """
        # Get the public key for this signer
        public_key = self._get_trusted_key(signer_id, algorithm)
        if not public_key:
            logger.warning("No trusted %s key found for signer %s", algorithm, signer_id)
            return False
        
        # Prepare the data that was signed
        signed_data = self._get_manifest_for_verification(cell)
        
        # Decode the signature from base64
        try:
            decoded_signature = base64.b64decode(signature)
        except Exception as e:
            logger.error("Failed to decode signature: %s", str(e))
            return False
        
        # Verify based on algorithm type
        try:
            if algorithm == "rsa":
                return self._verify_rsa_signature(signed_data, decoded_signature, public_key)
            elif algorithm == "ecdsa":
                return self._verify_ecdsa_signature(signed_data, decoded_signature, public_key)
            else:
                logger.error("Unsupported classical algorithm: %s", algorithm)
                return False
        except Exception as e:
            logger.error("Classical signature verification error: %s", str(e))
            return False
    
    async def _verify_hybrid_signature(self, cell: Cell, signature: Dict[str, str], 
                                     signer_id: str) -> bool:
        """
        Verify a hybrid signature (both classical and quantum).
        
        In hybrid mode, both signatures must be valid for the verification to pass.
        This provides defense in depth against both classical and quantum threats.
        
        Args:
            cell: The cell being verified
            signature: Dictionary containing both classical and quantum signatures
            signer_id: ID of the signer
            
        Returns:
            True if both signatures are valid, False otherwise
        """
        # Check that both signature components are present
        if "classical" not in signature or "quantum" not in signature:
            logger.error("Missing signature component in hybrid signature")
            return False
        
        if "algorithm" not in signature:
            logger.error("Missing algorithm specification in hybrid signature")
            return False
        
        # Verify classical signature first
        classical_valid = self._verify_classical_signature(
            cell,
            signature["classical"],
            signer_id,
            signature["algorithm"]
        )
        
        if not classical_valid:
            logger.warning("Classical component of hybrid signature is invalid")
            return False
        
        # Verify quantum signature
        quantum_valid = await self._verify_quantum_signature(
            cell,
            signature["quantum"],
            signer_id
        )
        
        if not quantum_valid:
            logger.warning("Quantum component of hybrid signature is invalid")
            return False
        
        # Both signatures are valid
        return True
    
    def _verify_cell_integrity(self, cell: Cell) -> bool:
        """
        Verify the integrity of cell contents against the manifest.
        
        Args:
            cell: The cell to verify
            
        Returns:
            True if the cell contents match the manifest, False otherwise
        """
        manifest = cell.manifest
        
        # Verify the cell code hash
        if hasattr(cell, 'code') and hasattr(manifest, 'code_hash'):
            code_hash = hashlib.sha256(cell.code).hexdigest()
            if code_hash != manifest.code_hash:
                logger.warning("Cell code hash mismatch for cell %s", cell.id)
                return False
        
        # Verify other cell attributes against manifest
        if hasattr(manifest, 'attributes'):
            for attr_name, expected_value in manifest.attributes.items():
                if hasattr(cell, attr_name):
                    actual_value = getattr(cell, attr_name)
                    if actual_value != expected_value:
                        logger.warning("Cell attribute mismatch: %s", attr_name)
                        return False
        
        # All integrity checks passed
        return True
    
    def _get_manifest_for_verification(self, cell: Cell) -> bytes:
        """
        Extract the manifest data that was signed.
        
        The manifest without the signature itself is what would have been signed.
        
        Args:
            cell: The cell being verified
            
        Returns:
            The manifest data as bytes
        """
        manifest_copy = cell.manifest.copy() if hasattr(cell.manifest, 'copy') else dict(cell.manifest)
        
        # Remove the signature from the copy
        if 'signature' in manifest_copy:
            del manifest_copy['signature']
        
        # Serialize to canonical form
        manifest_json = json.dumps(manifest_copy, sort_keys=True)
        return manifest_json.encode('utf-8')
    
    def _get_trusted_key(self, signer_id: str, key_type: str) -> Optional[str]:
        """
        Get a trusted public key for a specific signer and key type.
        
        Args:
            signer_id: ID of the signer
            key_type: Type of key ("rsa", "ecdsa", "quantum")
            
        Returns:
            Public key as string, or None if not found
        """
        if signer_id not in self.trusted_keys:
            return None
        
        signer_keys = self.trusted_keys[signer_id]
        return signer_keys.get(key_type)
    
    def _verify_rsa_signature(self, data: bytes, signature: bytes, public_key: str) -> bool:
        """
        Verify an RSA signature.
        
        Args:
            data: The data that was signed
            signature: The signature bytes
            public_key: The RSA public key
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Load the public key
            public_key_obj = load_pem_public_key(public_key.encode())
            
            # Verify the signature
            public_key_obj.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # If we reach here, verification succeeded
            return True
            
        except InvalidSignature:
            logger.warning("RSA signature verification failed - invalid signature")
            return False
        except Exception as e:
            logger.error("RSA verification error: %s", str(e))
            return False
    
    def _verify_ecdsa_signature(self, data: bytes, signature: bytes, public_key: str) -> bool:
        """
        Verify an ECDSA signature.
        
        Args:
            data: The data that was signed
            signature: The signature bytes
            public_key: The ECDSA public key
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Load the public key
            public_key_obj = load_pem_public_key(public_key.encode())
            
            # Verify the signature
            public_key_obj.verify(
                signature,
                data,
                ec.ECDSA(hashes.SHA256())
            )
            
            # If we reach here, verification succeeded
            return True
            
        except InvalidSignature:
            logger.warning("ECDSA signature verification failed - invalid signature")
            return False
        except Exception as e:
            logger.error("ECDSA verification error: %s", str(e))
            return False
    
    def _load_trusted_keys(self):
        """
        Load trusted keys from secure storage.
        """
        # In a real implementation, this would load from a secure key store
        # Here we'll provide a more realistic implementation that reads from files
        
        self.trusted_keys = {}
        keys_path = self.config.trusted_keys_path or "/etc/qcc/trusted_keys"
        
        try:
            # Check if the keys directory exists
            if not os.path.exists(keys_path):
                logger.warning("Trusted keys directory not found: %s", keys_path)
                # Fall back to sample keys for development
                self._load_development_keys()
                return
                
            # Read each signer's keys
            for signer_dir in os.listdir(keys_path):
                signer_path = os.path.join(keys_path, signer_dir)
                if not os.path.isdir(signer_path):
                    continue
                    
                # Initialize key dictionary for this signer
                self.trusted_keys[signer_dir] = {}
                
                # Load RSA key if present
                rsa_key_path = os.path.join(signer_path, "rsa_public.pem")
                if os.path.exists(rsa_key_path):
                    with open(rsa_key_path, 'r') as f:
                        self.trusted_keys[signer_dir]["rsa"] = f.read()
                
                # Load ECDSA key if present
                ecdsa_key_path = os.path.join(signer_path, "ecdsa_public.pem")
                if os.path.exists(ecdsa_key_path):
                    with open(ecdsa_key_path, 'r') as f:
                        self.trusted_keys[signer_dir]["ecdsa"] = f.read()
                
                # Load quantum key if present
                quantum_key_path = os.path.join(signer_path, "quantum_public.key")
                if os.path.exists(quantum_key_path):
                    with open(quantum_key_path, 'r') as f:
                        self.trusted_keys[signer_dir]["quantum"] = f.read()
            
            logger.info("Loaded trusted keys for %d signers from %s", 
                       len(self.trusted_keys), keys_path)
                
        except Exception as e:
            logger.error("Error loading trusted keys: %s", str(e))
            # Fall back to sample keys for development
            self._load_development_keys()
    
    def _load_development_keys(self):
        """
        Load sample keys for development and testing.
        
        In production, this function would not be used, as keys would
        come from a secure key store.
        """
        logger.warning("Loading development keys - NOT FOR PRODUCTION USE")
        
        # Sample RSA keys (just the beginning of the key for demonstration)
        sample_rsa_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu8LW+RhUmXV5soRRSWw0
9/O9YW0NLUzZDH5L8qtR57FcjTBRMJ6LIRzXEpgAUwRUfYRhaJSPHFLfdIP34iY+
RUeBppBbZKPr1jbNrU9MHeXkBLmC6zKmNbZz8YBrAGjHMO8x9SmQeHSm+3nkGZM+
XpTVbjKJkDET9Zlr7V/xxRhZnkQN++aOYfUZ/DrXnHXtnMw/n6UYtFt8MIlk6zRY
6O5IA3PrEqwZjEJT+9IZT04bCsGdJ0XVHTaMLHBNI36MolA2Vatb0Feg+UBscCla
t0+qqggD9Z2CZWymbTKmdK8vh4/Rz1CaPzbxQxAdiZOEiEYvDNSaifZGKqRTXZx3
wQIDAQAB
-----END PUBLIC KEY-----"""

        # Sample ECDSA keys (just the beginning of the key for demonstration)
        sample_ecdsa_key = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEZolTLYQXnrLfn3MCjbYZe5zipPXN
bvJtKkJBv1VOcgnYPwlMYnD/JLkuR8MEcAbBKMEdwCS1GUiUsQsrJBdlPQ==
-----END PUBLIC KEY-----"""

        # Sample quantum keys (for demonstration only, not real quantum keys)
        sample_quantum_key = "QUANTUM_PUBLIC_KEY_PLACEHOLDER"

        # Store sample keys
        self.trusted_keys = {
            "provider1": {
                "rsa": sample_rsa_key,
                "ecdsa": sample_ecdsa_key,
                "quantum": sample_quantum_key
            },
            "provider2": {
                "rsa": sample_rsa_key,
                "ecdsa": sample_ecdsa_key,
                "quantum": sample_quantum_key
            }
        }

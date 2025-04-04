"""
Anonymization techniques for the QCC Quantum Trail.

This module provides mechanisms to anonymize user data within the Quantum 
Trail system, ensuring that patterns can be recognized without revealing 
user identities.
"""

import hashlib
import os
import time
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)

@dataclass
class AnonymizerConfig:
    """Configuration for the Anonymizer."""
    
    # Determines how often identifiers are rotated (in seconds)
    rotation_period: int = 86400  # Default: 24 hours
    
    # Strength of hash algorithm (iterations)
    hash_iterations: int = 10000
    
    # Which fields to always anonymize
    sensitive_fields: Set[str] = None
    
    # Which fields to never anonymize
    preserved_fields: Set[str] = None
    
    # Whether to use deterministic or probabilistic anonymization
    deterministic: bool = True
    
    # Salt rotation strategy
    rotate_salt: bool = True
    
    # Use quantum-resistant hash function
    quantum_resistant: bool = True
    
    def __post_init__(self):
        """Initialize default values for sets."""
        if self.sensitive_fields is None:
            self.sensitive_fields = {"user_id", "device_id", "ip_address", 
                                     "email", "name", "session_id"}
        
        if self.preserved_fields is None:
            self.preserved_fields = {"timestamp", "cell_type", "capability",
                                     "performance_metrics"}


class Anonymizer:
    """
    Provides anonymization capabilities for the Quantum Trail system.
    
    This class implements various techniques to anonymize user data while
    preserving the ability to recognize patterns and provide personalization.
    """
    
    def __init__(self, config: AnonymizerConfig = None):
        """
        Initialize the Anonymizer.
        
        Args:
            config: Configuration parameters for anonymization
        """
        self.config = config or AnonymizerConfig()
        
        # Generate initial salt
        self._salt = os.urandom(32)
        self._salt_created_at = time.time()
        
        # Create identifier mappings
        self._id_mappings = {}
        
        # Load quantum-resistant hash function if requested
        if self.config.quantum_resistant:
            try:
                # In production, this would use a PQC library
                # For now, use SHA3-512 which has better resistance than SHA2
                self._hash_function = hashlib.sha3_512
                logger.info("Using SHA3-512 for anonymization (quantum resistance)")
            except AttributeError:
                logger.warning("SHA3 not available, falling back to SHA-256")
                self._hash_function = hashlib.sha256
        else:
            self._hash_function = hashlib.sha256
            
        logger.info(f"Anonymizer initialized with rotation period: {self.config.rotation_period}s")
        
    def anonymize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize the provided data.
        
        Args:
            data: Data to anonymize
            
        Returns:
            Anonymized data
        """
        # Check if salt rotation is needed
        self._check_rotation()
        
        # Create a copy to avoid modifying the original
        anonymized = data.copy()
        
        # Process each field
        for field, value in data.items():
            if field in self.config.sensitive_fields and field not in self.config.preserved_fields:
                anonymized[field] = self._anonymize_field(field, value)
        
        return anonymized
    
    def deanonymize(self, field: str, anonymous_value: str) -> Optional[str]:
        """
        Deanonymize a field if possible (only works for deterministic anonymization).
        
        Args:
            field: Field name
            anonymous_value: Anonymized value
            
        Returns:
            Original value if found, None otherwise
        """
        if not self.config.deterministic:
            logger.warning("Cannot deanonymize with non-deterministic configuration")
            return None
        
        # Check mappings
        if field in self._id_mappings:
            # Reverse lookup in the mapping
            for original, anon in self._id_mappings[field].items():
                if anon == anonymous_value:
                    return original
        
        return None
    
    def _anonymize_field(self, field: str, value: Any) -> Any:
        """
        Anonymize a specific field.
        
        Args:
            field: Field name
            value: Value to anonymize
            
        Returns:
            Anonymized value
        """
        # Skip None values
        if value is None:
            return None
        
        # Convert value to string if not already
        if not isinstance(value, str):
            value = str(value)
        
        # For deterministic anonymization, use a mapping
        if self.config.deterministic:
            return self._deterministic_anonymize(field, value)
        else:
            # For non-deterministic, just generate a new random identifier
            return str(uuid.uuid4())
    
    def _deterministic_anonymize(self, field: str, value: str) -> str:
        """
        Deterministically anonymize a value.
        
        Args:
            field: Field name
            value: Value to anonymize
            
        Returns:
            Anonymized value
        """
        # Initialize mapping for this field if needed
        if field not in self._id_mappings:
            self._id_mappings[field] = {}
        
        # Check if we already have a mapping for this value
        if value in self._id_mappings[field]:
            return self._id_mappings[field][value]
        
        # Create a new anonymous ID
        anonymous_id = self._create_hash(field, value)
        
        # Store the mapping
        self._id_mappings[field][value] = anonymous_id
        
        return anonymous_id
    
    def _create_hash(self, field: str, value: str) -> str:
        """
        Create a hash for anonymization.
        
        Args:
            field: Field name
            value: Value to hash
            
        Returns:
            Hash value as hexadecimal string
        """
        # Combine field, value, and salt
        data = f"{field}:{value}".encode('utf-8')
        
        # Perform hashing with iterations for added security
        result = self._salt
        for _ in range(self.config.hash_iterations):
            h = self._hash_function()
            h.update(result + data)
            result = h.digest()
        
        # Return as hex string
        return result.hex()
    
    def _check_rotation(self) -> None:
        """Check if salt rotation is needed and rotate if necessary."""
        if not self.config.rotate_salt:
            return
        
        current_time = time.time()
        
        if current_time - self._salt_created_at > self.config.rotation_period:
            logger.info("Rotating anonymization salt")
            
            # Generate new salt
            self._salt = os.urandom(32)
            self._salt_created_at = current_time
            
            # Clear mappings when salt rotates
            self._id_mappings = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the anonymizer.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "salt_age_seconds": int(time.time() - self._salt_created_at),
            "mappings_count": {field: len(mappings) for field, mappings in self._id_mappings.items()},
            "config": {
                "rotation_period": self.config.rotation_period,
                "hash_iterations": self.config.hash_iterations,
                "deterministic": self.config.deterministic,
                "quantum_resistant": self.config.quantum_resistant
            }
        }
        
        return stats

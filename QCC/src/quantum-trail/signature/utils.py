"""
Utility functions for the Quantum Trail Signature module.

This module provides helper functions for signature generation, encoding/decoding,
hashing, and other cryptographic operations.
"""

import os
import base64
import json
import time
import hashlib
import secrets
import logging
from typing import Dict, Any, Tuple, Optional, Union

logger = logging.getLogger(__name__)

def encode_signature(signature_data: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Encode a signature and its payload into a single string.
    
    Args:
        signature_data: Signature data and metadata
        payload: Data that was signed
        
    Returns:
        Base64-encoded string containing signature and payload
    """
    # Combine signature and payload
    combined = {
        "signature": signature_data,
        "payload": payload
    }
    
    # Encode as JSON and then Base64
    json_data = json.dumps(combined)
    encoded = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    
    return encoded

def decode_signature(encoded_signature: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Decode a signature string into signature data and payload.
    
    Args:
        encoded_signature: Base64-encoded signature string
        
    Returns:
        Tuple containing signature data and payload
        
    Raises:
        ValueError: If the signature format is invalid
    """
    try:
        # Decode Base64 and then JSON
        json_data = base64.b64decode(encoded_signature).decode('utf-8')
        combined = json.loads(json_data)
        
        # Extract signature and payload
        if "signature" not in combined or "payload" not in combined:
            raise ValueError("Invalid signature format: missing signature or payload")
        
        return combined["signature"], combined["payload"]
    
    except Exception as e:
        logger.error(f"Error decoding signature: {str(e)}")
        raise ValueError(f"Invalid signature format: {str(e)}")

def hash_data(data: Any) -> str:
    """
    Generate a secure hash of data.
    
    Args:
        data: Data to hash
        
    Returns:
        Hexadecimal hash string
    """
    if data is None:
        return None
    
    # Convert to canonical JSON if it's a dictionary or list
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True, separators=(',', ':'))
    elif not isinstance(data, (str, bytes)):
        data = str(data)
    
    # Convert to bytes if necessary
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Generate SHA-256 hash
    return hashlib.sha256(data).hexdigest()

def generate_nonce(length: int = 16) -> str:
    """
    Generate a secure random nonce.
    
    Args:
        length: Length of the nonce in bytes
        
    Returns:
        Hexadecimal nonce string
    """
    # Generate random bytes and convert to hexadecimal
    return secrets.token_hex(length)

def verify_integrity(data: Dict[str, Any], expected_hash: str) -> bool:
    """
    Verify the integrity of data by comparing its hash.
    
    Args:
        data: Data to verify
        expected_hash: Expected hash value
        
    Returns:
        True if the hash matches, False otherwise
    """
    # Calculate hash of the data
    actual_hash = hash_data(data)
    
    # Compare hashes
    return actual_hash == expected_hash

def derive_key(seed: str, salt: Optional[str] = None, iterations: int = 100000) -> bytes:
    """
    Derive a cryptographic key from a seed.
    
    Args:
        seed: Seed to derive key from
        salt: Optional salt value
        iterations: Number of iterations for key derivation
        
    Returns:
        Derived key as bytes
    """
    # Use PBKDF2 for key derivation
    if salt is None:
        salt = os.urandom(16)
    
    # Convert seed to bytes
    if isinstance(seed, str):
        seed = seed.encode('utf-8')
    
    # Use PBKDF2-HMAC with SHA-256
    return hashlib.pbkdf2_hmac('sha256', seed, salt, iterations, 32)

def time_safe_compare(a: str, b: str) -> bool:
    """
    Compare two strings in a way that is resistant to timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if the strings are equal, False otherwise
    """
    # Use secrets.compare_digest to prevent timing attacks
    if isinstance(a, str):
        a = a.encode('utf-8')
    if isinstance(b, str):
        b = b.encode('utf-8')
    
    return secrets.compare_digest(a, b)

def get_timestamp() -> int:
    """
    Get the current timestamp in seconds since the epoch.
    
    Returns:
        Current timestamp
    """
    return int(time.time())

def format_timestamp(timestamp: int) -> str:
    """
    Format a timestamp as ISO 8601.
    
    Args:
        timestamp: Timestamp in seconds since the epoch
        
    Returns:
        Formatted timestamp string
    """
    # Convert timestamp to ISO 8601 format
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(timestamp))

def generate_id(prefix: str = 'sig') -> str:
    """
    Generate a unique ID.
    
    Args:
        prefix: Prefix for the ID
        
    Returns:
        Unique ID string
    """
    # Generate a UUID-like identifier
    random_bytes = os.urandom(16)
    random_hex = ''.join(f'{b:02x}' for b in random_bytes)
    timestamp = int(time.time())
    
    return f"{prefix}_{timestamp}_{random_hex}"

"""
Quantum Trail Signature Module

This module provides quantum-resistant signature generation and verification for the QCC system.
It leverages post-quantum cryptographic algorithms to create unforgeable signatures that
uniquely identify cell assemblies while preserving privacy.

The core components include:
- Signature generation using quantum-resistant algorithms
- Signature verification mechanisms
- Algorithm implementations (CRYSTALS-Dilithium, SPHINCS+)
- Utility functions for signature management
"""

from .generator import SignatureGenerator
from .verifier import SignatureVerifier
from .algorithms import (
    DilithiumSigner,
    SPHINCSPlusSigner,
    HybridSigner,
    SignatureAlgorithm
)
from .utils import (
    encode_signature,
    decode_signature,
    generate_nonce,
    hash_data,
    verify_integrity
)

__all__ = [
    'SignatureGenerator',
    'SignatureVerifier',
    'DilithiumSigner',
    'SPHINCSPlusSigner',
    'HybridSigner',
    'SignatureAlgorithm',
    'encode_signature',
    'decode_signature',
    'generate_nonce',
    'hash_data',
    'verify_integrity'
]

__version__ = '1.0.0'

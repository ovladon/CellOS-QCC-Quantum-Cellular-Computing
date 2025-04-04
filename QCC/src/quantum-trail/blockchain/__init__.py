"""
Blockchain implementation for the Quantum Trail system.

This module provides the blockchain infrastructure for the Quantum Trail,
which maintains anonymous signatures of successful cell assemblies,
enabling personalization without identification.
"""

from .blockchain import Blockchain
from .block import Block
from .transaction import Transaction
from .consensus import Consensus
from .crypto import (
    generate_quantum_resistant_keys,
    create_quantum_signature,
    verify_quantum_signature,
    hash_data,
    generate_quantum_signature
)
from .node import BlockchainNode

__all__ = [
    'Blockchain',
    'Block',
    'Transaction',
    'Consensus',
    'generate_quantum_resistant_keys',
    'create_quantum_signature',
    'verify_quantum_signature',
    'hash_data',
    'generate_quantum_signature',
    'BlockchainNode'
]

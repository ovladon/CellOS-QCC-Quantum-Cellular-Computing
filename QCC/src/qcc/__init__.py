"""
QCC: Quantum Cellular Computing

A framework for dynamic, intent-based computing using specialized
AI cells that assemble on demand.
"""

__version__ = "0.1.0"
__author__ = "QCC Team"
__license__ = "MIT"

# Import key components for easier access
from qcc.assembler.core.assembler import CellAssembler
from qcc.quantum_trail.blockchain.ledger import QuantumTrailLedger
from qcc.providers.repository.manager import ProviderManager
from qcc.common.models import Solution

# Define package exports
__all__ = [
    "CellAssembler",
    "QuantumTrailLedger",
    "ProviderManager",
    "Solution"
]

"""
Privacy mechanisms for the QCC Quantum Trail system.

This module provides privacy-preserving techniques for the Quantum Trail,
enabling personalization without compromising user privacy through techniques
like anonymization, zero-knowledge proofs, and differential privacy.
"""

from .anonymizer import Anonymizer, AnonymizerConfig
from .zero_knowledge import ZeroKnowledgeProver, ZeroKnowledgeVerifier
from .differential_privacy import DifferentialPrivacy, PrivacyBudget
from .privacy_manager import PrivacyManager, PrivacyPolicy

__all__ = [
    'Anonymizer',
    'AnonymizerConfig',
    'ZeroKnowledgeProver',
    'ZeroKnowledgeVerifier',
    'DifferentialPrivacy',
    'PrivacyBudget',
    'PrivacyManager',
    'PrivacyPolicy'
]

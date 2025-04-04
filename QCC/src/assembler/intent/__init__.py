"""
User intent interpretation module for the QCC Assembler.

This module provides functionality for analyzing user requests
and determining the required capabilities and configuration.
"""

from .interpreter import IntentInterpreter
from .models import IntentAnalysis, RequiredCapability
from .patterns import intentPatterns, capabilityMapping

__all__ = [
    'IntentInterpreter',
    'IntentAnalysis',
    'RequiredCapability',
    'intentPatterns',
    'capabilityMapping'
]

"""
Cell verification system for the QCC providers.

This package provides modules for verifying cells before they are registered,
distributed, or executed within the QCC ecosystem. It ensures cells meet the
security, compatibility, and integrity requirements of the system.

The verification system is a critical security component that helps maintain
trust in the cell ecosystem by validating that cells:
- Come from trusted sources
- Have not been tampered with
- Are free from security vulnerabilities
- Request only appropriate permissions
- Meet the required cell interface specifications
"""

from .verifier import CellVerifier
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

__all__ = [
    'CellVerifier',
    'SignatureValidator',
    'SecurityScanner',
    'CompatibilityChecker',
    'PermissionValidator',
    'VerificationError',
    'SignatureVerificationError',
    'SecurityViolationError',
    'CompatibilityError',
    'PermissionError'
]

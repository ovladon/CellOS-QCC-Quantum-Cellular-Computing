"""
Exception classes for the QCC Assembler.

This module defines custom exception classes for the assembler,
providing clear error classification and handling.
"""

class AssemblerError(Exception):
    """Base class for all assembler exceptions."""
    
    def __init__(self, message: str = "An error occurred in the assembler"):
        self.message = message
        super().__init__(self.message)


class InvalidIntentError(AssemblerError):
    """Raised when user intent cannot be properly interpreted."""
    
    def __init__(self, message: str = "Could not interpret user intent"):
        super().__init__(message)


class CapabilityNotFoundError(AssemblerError):
    """Raised when a required capability cannot be found."""
    
    def __init__(self, capability: str):
        message = f"Could not find provider for capability: {capability}"
        super().__init__(message)


class CellActivationError(AssemblerError):
    """Raised when a cell cannot be activated."""
    
    def __init__(self, cell_id: str, reason: str = "unknown reason"):
        message = f"Failed to activate cell {cell_id}: {reason}"
        super().__init__(message)


class CellConnectionError(AssemblerError):
    """Raised when cells cannot be connected."""
    
    def __init__(self, source_id: str, target_id: str, reason: str = "unknown reason"):
        message = f"Failed to connect cell {source_id} to {target_id}: {reason}"
        super().__init__(message)


class ResourceExhaustionError(AssemblerError):
    """Raised when system resources are exhausted."""
    
    def __init__(self, resource_type: str = "resources"):
        message = f"System {resource_type} exhausted"
        super().__init__(message)


class ConfigurationError(AssemblerError):
    """Raised when there is an error in the assembler configuration."""
    
    def __init__(self, setting: str, message: str = "Invalid configuration"):
        message = f"{message}: {setting}"
        super().__init__(message)


class QuantumTrailError(AssemblerError):
    """Raised when there is an error with the quantum trail system."""
    
    def __init__(self, operation: str, message: str = "Quantum trail error"):
        message = f"{message} during {operation}"
        super().__init__(message)


class SecurityError(AssemblerError):
    """Raised when there is a security-related error."""
    
    def __init__(self, message: str = "Security check failed"):
        super().__init__(message)

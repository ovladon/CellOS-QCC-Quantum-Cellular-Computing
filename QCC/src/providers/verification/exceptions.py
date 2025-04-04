"""
Exception classes for the QCC verification system.

This module defines custom exceptions used by the cell verification
system to provide detailed information about verification failures.
"""

class VerificationError(Exception):
    """
    Base exception for all verification errors.
    
    Used when a cell fails verification for any reason.
    """
    
    def __init__(self, message: str, cell_id: str = None):
        """
        Initialize the verification error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
        """
        if cell_id:
            message = f"Cell {cell_id}: {message}"
        super().__init__(message)
        self.cell_id = cell_id


class SignatureVerificationError(VerificationError):
    """
    Raised when cell signature verification fails.
    
    This indicates that a cell's signature could not be validated,
    suggesting it may not come from a trusted source or has been tampered with.
    """
    
    def __init__(self, message: str, cell_id: str = None, signer_id: str = None):
        """
        Initialize the signature verification error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            signer_id: Optional ID of the purported signer
        """
        if signer_id:
            message = f"{message} (Signer: {signer_id})"
        super().__init__(message, cell_id)
        self.signer_id = signer_id


class SecurityViolationError(VerificationError):
    """
    Raised when a cell fails security scanning.
    
    This indicates that a cell contains security vulnerabilities or
    violates security policies that could pose a risk to the system.
    """
    
    def __init__(self, message: str, cell_id: str = None, 
                 issue_type: str = None, severity: str = None):
        """
        Initialize the security violation error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            issue_type: Type of security issue
            severity: Severity level of the issue
        """
        if severity and issue_type:
            message = f"{severity.upper()} security issue ({issue_type}): {message}"
        elif issue_type:
            message = f"Security issue ({issue_type}): {message}"
        
        super().__init__(message, cell_id)
        self.issue_type = issue_type
        self.severity = severity


class CompatibilityError(VerificationError):
    """
    Raised when a cell fails compatibility checking.
    
    This indicates that a cell does not adhere to required interfaces
    or standards, making it incompatible with the QCC ecosystem.
    """
    
    def __init__(self, message: str, cell_id: str = None, 
                 interface_version: str = None):
        """
        Initialize the compatibility error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            interface_version: Cell's interface version
        """
        if interface_version:
            message = f"Compatibility error (interface v{interface_version}): {message}"
        super().__init__(message, cell_id)
        self.interface_version = interface_version


class PermissionError(VerificationError):
    """
    Raised when a cell fails permission validation.
    
    This indicates that a cell requests permissions that are inappropriate,
    overly broad, or not properly justified for its declared capabilities.
    """
    
    def __init__(self, message: str, cell_id: str = None, 
                 permission: str = None):
        """
        Initialize the permission error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            permission: Name of the problematic permission
        """
        if permission:
            message = f"Permission error ({permission}): {message}"
        super().__init__(message, cell_id)
        self.permission = permission


class VerificationTimeoutError(VerificationError):
    """
    Raised when verification takes too long to complete.
    
    This may indicate that a cell is too complex to verify within
    reasonable time constraints, or that verification is stuck.
    """
    
    def __init__(self, message: str, cell_id: str = None, 
                 timeout_seconds: float = None):
        """
        Initialize the verification timeout error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            timeout_seconds: Seconds before timeout occurred
        """
        if timeout_seconds:
            message = f"Verification timed out after {timeout_seconds:.1f}s: {message}"
        super().__init__(message, cell_id)
        self.timeout_seconds = timeout_seconds


class ValidationResourceExceededError(VerificationError):
    """
    Raised when verification exceeds resource limits.
    
    This may indicate that a cell is too resource-intensive to verify,
    potentially because it's too large or complex.
    """
    
    def __init__(self, message: str, cell_id: str = None, 
                 resource_type: str = None, limit: float = None,
                 actual: float = None):
        """
        Initialize the resource exceeded error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            resource_type: Type of resource that was exceeded
            limit: Resource limit
            actual: Actual resource usage
        """
        if resource_type and limit is not None and actual is not None:
            message = f"Resource limit exceeded ({resource_type}): {actual} > {limit}. {message}"
        elif resource_type:
            message = f"Resource limit exceeded ({resource_type}): {message}"
        super().__init__(message, cell_id)
        self.resource_type = resource_type
        self.limit = limit
        self.actual = actual


class UnknownCellTypeError(VerificationError):
    """
    Raised when verification encounters an unknown cell type.
    
    This indicates that the cell format or structure is not recognized
    by the verification system.
    """
    
    def __init__(self, message: str, cell_id: str = None, 
                 detected_type: str = None):
        """
        Initialize the unknown cell type error.
        
        Args:
            message: Error message
            cell_id: Optional ID of the cell that failed verification
            detected_type: Type that was detected, if any
        """
        if detected_type:
            message = f"Unknown cell type (detected: {detected_type}): {message}"
        super().__init__(message, cell_id)
        self.detected_type = detected_type

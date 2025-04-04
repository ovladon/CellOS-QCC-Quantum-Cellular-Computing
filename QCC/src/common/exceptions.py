"""
Exceptions for the Quantum Cellular Computing (QCC) system.

This module defines a hierarchy of exceptions used throughout the QCC
architecture to provide consistent error handling and reporting.
"""

class QCCError(Exception):
    """Base exception class for all QCC errors."""
    
    def __init__(self, message, error_code=None, details=None):
        """
        Initialize QCC error.
        
        Args:
            message: Error message
            error_code: Optional error code
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self):
        """String representation of the error."""
        if self.error_code:
            return f"{self.error_code}: {self.message}"
        return self.message
    
    def to_dict(self):
        """Convert the error to a dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


# Assembler Exceptions

class AssemblerError(QCCError):
    """Base exception for errors in the Assembler module."""
    pass


class InvalidIntentError(AssemblerError):
    """Error raised when user intent cannot be interpreted."""
    
    def __init__(self, message, confidence=None, alternatives=None, **kwargs):
        """
        Initialize intent error.
        
        Args:
            message: Error message
            confidence: Confidence level of intent interpretation
            alternatives: Alternative interpretations
        """
        details = kwargs.get('details', {})
        details.update({
            "confidence": confidence,
            "alternatives": alternatives
        })
        super().__init__(message, error_code="INTENT_ERROR", details=details)


class CellRequestError(AssemblerError):
    """Error raised when requested cells cannot be obtained."""
    
    def __init__(self, message, capability=None, providers_tried=None, **kwargs):
        """
        Initialize cell request error.
        
        Args:
            message: Error message
            capability: Requested capability
            providers_tried: List of providers that were tried
        """
        details = kwargs.get('details', {})
        details.update({
            "capability": capability,
            "providers_tried": providers_tried
        })
        super().__init__(message, error_code="CELL_REQUEST_ERROR", details=details)


class SecurityVerificationError(AssemblerError):
    """Error raised when cell security verification fails."""
    
    def __init__(self, message, cell_id=None, verification_stage=None, **kwargs):
        """
        Initialize verification error.
        
        Args:
            message: Error message
            cell_id: ID of the cell that failed verification
            verification_stage: Stage at which verification failed
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "verification_stage": verification_stage
        })
        super().__init__(message, error_code="SECURITY_ERROR", details=details)


# Provider Exceptions

class ProviderError(QCCError):
    """Base exception for errors in the Provider module."""
    pass


class RepositoryError(ProviderError):
    """Error raised when operating on the cell repository."""
    
    def __init__(self, message, operation=None, **kwargs):
        """
        Initialize repository error.
        
        Args:
            message: Error message
            operation: Repository operation that failed
        """
        details = kwargs.get('details', {})
        details.update({
            "operation": operation
        })
        super().__init__(message, error_code="REPOSITORY_ERROR", details=details)


class CellNotFoundError(RepositoryError):
    """Error raised when a requested cell is not found."""
    
    def __init__(self, message, cell_id=None, cell_type=None, capability=None, **kwargs):
        """
        Initialize cell not found error.
        
        Args:
            message: Error message
            cell_id: ID of the cell
            cell_type: Type of the cell
            capability: Requested capability
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "cell_type": cell_type,
            "capability": capability
        })
        super().__init__(message, error_code="CELL_NOT_FOUND", details=details, operation="get_cell")


class DistributionError(ProviderError):
    """Error raised during cell distribution."""
    
    def __init__(self, message, cell_id=None, stage=None, **kwargs):
        """
        Initialize distribution error.
        
        Args:
            message: Error message
            cell_id: ID of the cell
            stage: Distribution stage where the error occurred
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "stage": stage
        })
        super().__init__(message, error_code="DISTRIBUTION_ERROR", details=details)


class VerificationError(ProviderError):
    """Error raised during cell verification."""
    
    def __init__(self, message, cell_id=None, verification_type=None, **kwargs):
        """
        Initialize verification error.
        
        Args:
            message: Error message
            cell_id: ID of the cell
            verification_type: Type of verification that failed
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "verification_type": verification_type
        })
        super().__init__(message, error_code="VERIFICATION_ERROR", details=details)


# Quantum Trail Exceptions

class QuantumTrailError(QCCError):
    """Base exception for errors in the Quantum Trail module."""
    pass


class LedgerError(QuantumTrailError):
    """Error raised when operating on the blockchain ledger."""
    
    def __init__(self, message, operation=None, **kwargs):
        """
        Initialize ledger error.
        
        Args:
            message: Error message
            operation: Ledger operation that failed
        """
        details = kwargs.get('details', {})
        details.update({
            "operation": operation
        })
        super().__init__(message, error_code="LEDGER_ERROR", details=details)


class BlockValidationError(LedgerError):
    """Error raised when block validation fails."""
    
    def __init__(self, message, block_index=None, validation_stage=None, **kwargs):
        """
        Initialize block validation error.
        
        Args:
            message: Error message
            block_index: Index of the block
            validation_stage: Stage of validation that failed
        """
        details = kwargs.get('details', {})
        details.update({
            "block_index": block_index,
            "validation_stage": validation_stage
        })
        super().__init__(message, error_code="BLOCK_VALIDATION_ERROR", details=details, operation="validate_block")


class TransactionValidationError(LedgerError):
    """Error raised when transaction validation fails."""
    
    def __init__(self, message, transaction_id=None, validation_stage=None, **kwargs):
        """
        Initialize transaction validation error.
        
        Args:
            message: Error message
            transaction_id: ID of the transaction
            validation_stage: Stage of validation that failed
        """
        details = kwargs.get('details', {})
        details.update({
            "transaction_id": transaction_id,
            "validation_stage": validation_stage
        })
        super().__init__(message, error_code="TRANSACTION_VALIDATION_ERROR", details=details, operation="validate_transaction")


# Cell Exceptions

class CellError(QCCError):
    """Base exception for errors in Cell implementation."""
    pass


class CellInitializationError(CellError):
    """Error raised when cell initialization fails."""
    
    def __init__(self, message, cell_id=None, initialization_stage=None, **kwargs):
        """
        Initialize cell initialization error.
        
        Args:
            message: Error message
            cell_id: ID of the cell
            initialization_stage: Initialization stage that failed
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "initialization_stage": initialization_stage
        })
        super().__init__(message, error_code="CELL_INITIALIZATION_ERROR", details=details)


class CellExecutionError(CellError):
    """Error raised when cell capability execution fails."""
    
    def __init__(self, message, cell_id=None, capability=None, parameters=None, **kwargs):
        """
        Initialize cell execution error.
        
        Args:
            message: Error message
            cell_id: ID of the cell
            capability: Capability being executed
            parameters: Execution parameters
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "capability": capability,
            "parameters": parameters
        })
        super().__init__(message, error_code="CELL_EXECUTION_ERROR", details=details)


class CellConnectionError(CellError):
    """Error raised when cell connection fails."""
    
    def __init__(self, message, source_cell_id=None, target_cell_id=None, connection_type=None, **kwargs):
        """
        Initialize cell connection error.
        
        Args:
            message: Error message
            source_cell_id: ID of the source cell
            target_cell_id: ID of the target cell
            connection_type: Type of connection
        """
        details = kwargs.get('details', {})
        details.update({
            "source_cell_id": source_cell_id,
            "target_cell_id": target_cell_id,
            "connection_type": connection_type
        })
        super().__init__(message, error_code="CELL_CONNECTION_ERROR", details=details)


# Runtime Exceptions

class RuntimeError(QCCError):
    """Base exception for errors in the Runtime module."""
    pass


class ResourceLimitExceededError(RuntimeError):
    """Error raised when a cell exceeds resource limits."""
    
    def __init__(self, message, cell_id=None, resource_type=None, limit=None, actual=None, **kwargs):
        """
        Initialize resource limit error.
        
        Args:
            message: Error message
            cell_id: ID of the cell
            resource_type: Type of resource (memory, CPU, etc.)
            limit: Resource limit
            actual: Actual resource usage
        """
        details = kwargs.get('details', {})
        details.update({
            "cell_id": cell_id,
            "resource_type": resource_type,
            "limit": limit,
            "actual": actual
        })
        super().__init__(message, error_code="RESOURCE_LIMIT_ERROR", details=details)


class TimeoutError(RuntimeError):
    """Error raised when an operation times out."""
    
    def __init__(self, message, operation=None, timeout_seconds=None, **kwargs):
        """
        Initialize timeout error.
        
        Args:
            message: Error message
            operation: Operation that timed out
            timeout_seconds: Timeout duration
        """
        details = kwargs.get('details', {})
        details.update({
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })
        super().__init__(message, error_code="TIMEOUT_ERROR", details=details)


# API Exceptions

class APIError(QCCError):
    """Base exception for API errors."""
    pass


class AuthenticationError(APIError):
    """Error raised when API authentication fails."""
    
    def __init__(self, message, auth_method=None, **kwargs):
        """
        Initialize authentication error.
        
        Args:
            message: Error message
            auth_method: Authentication method used
        """
        details = kwargs.get('details', {})
        details.update({
            "auth_method": auth_method
        })
        super().__init__(message, error_code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(APIError):
    """Error raised when API authorization fails."""
    
    def __init__(self, message, required_permission=None, **kwargs):
        """
        Initialize authorization error.
        
        Args:
            message: Error message
            required_permission: Permission required for the operation
        """
        details = kwargs.get('details', {})
        details.update({
            "required_permission": required_permission
        })
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)


class ValidationError(APIError):
    """Error raised when API input validation fails."""
    
    def __init__(self, message, field=None, value=None, constraint=None, **kwargs):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
            constraint: Validation constraint
        """
        details = kwargs.get('details', {})
        details.update({
            "field": field,
            "value": value,
            "constraint": constraint
        })
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class RateLimitError(APIError):
    """Error raised when API rate limit is exceeded."""
    
    def __init__(self, message, limit=None, reset_time=None, **kwargs):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            limit: Rate limit
            reset_time: Time when the limit resets
        """
        details = kwargs.get('details', {})
        details.update({
            "limit": limit,
            "reset_time": reset_time
        })
        super().__init__(message, error_code="RATE_LIMIT_ERROR", details=details)

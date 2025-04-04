"""
Common functionality for the Quantum Cellular Computing (QCC) system.

This module provides shared components, utilities, and models that are used
across different parts of the QCC architecture.
"""

from .exceptions import (
    QCCError,
    AssemblerError,
    InvalidIntentError,
    CellRequestError,
    SecurityVerificationError,
    ProviderError,
    RepositoryError,
    DistributionError,
    VerificationError,
    LedgerError,
    BlockValidationError,
    TransactionValidationError,
    QuantumTrailError
)

from .models import (
    Cell,
    Solution,
    CellConfiguration,
    QuantumSignature,
    AssemblyPattern,
    CapabilitySpecification
)

from .utils import (
    version_info,
    get_device_info,
    get_timestamp,
    generate_id,
    hash_data,
    encode_data,
    decode_data
)

from .config import (
    load_config,
    get_config_path,
    merge_configs
)

from .logging import setup_logger, get_logger

# Module version
__version__ = '1.0.0'

# Export all common functionality
__all__ = [
    # Exceptions
    'QCCError',
    'AssemblerError',
    'InvalidIntentError',
    'CellRequestError',
    'SecurityVerificationError',
    'ProviderError',
    'RepositoryError',
    'DistributionError',
    'VerificationError',
    'LedgerError',
    'BlockValidationError',
    'TransactionValidationError',
    'QuantumTrailError',
    
    # Models
    'Cell',
    'Solution',
    'CellConfiguration',
    'QuantumSignature',
    'AssemblyPattern',
    'CapabilitySpecification',
    
    # Utilities
    'version_info',
    'get_device_info',
    'get_timestamp',
    'generate_id',
    'hash_data',
    'encode_data',
    'decode_data',
    
    # Configuration
    'load_config',
    'get_config_path',
    'merge_configs',
    
    # Logging
    'setup_logger',
    'get_logger'
]

"""
QCC Unit Tests

This package contains unit tests for individual components of the Quantum Cellular Computing (QCC) project.
Unit tests focus on testing the functionality of specific components in isolation, with dependencies
being mocked or stubbed as necessary.

Test modules in this package are organized by component:
- test_assembler.py: Tests for the cell assembler
- test_cells.py: Tests for cell functionality
- test_intent.py: Tests for intent interpretation
- test_security.py: Tests for security mechanisms
- test_quantum_trail.py: Tests for quantum trail system
- test_models.py: Tests for data models
- test_providers.py: Tests for cell providers
"""

# Import common test utilities
from ..conftest import (
    mock_intent_interpreter,
    mock_security_manager,
    mock_cell_runtime,
    mock_quantum_trail,
    mock_repository_manager,
    mock_cell,
    mock_solution,
    mock_cell_configuration
)

# Define unit test specific constants
UNIT_TEST_TIMEOUT = 5  # seconds

"""
QCC Integration Tests

This package contains integration tests for the Quantum Cellular Computing (QCC) project.
Integration tests verify that different components of the system work together correctly,
focusing on component interactions rather than isolated functionality.

These tests require a running QCC environment and may use actual (or mock) providers,
cells, and quantum trail implementations to test end-to-end scenarios.

Test modules in this package:
- test_system.py: End-to-end tests of the entire QCC system
- test_assembler_provider.py: Tests for assembler-provider interactions
- test_cell_communication.py: Tests for inter-cell communication
- test_quantum_trail_integration.py: Tests for quantum trail integration
- test_resource_management.py: Tests for resource allocation and management
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'integration_tests.log'))
    ]
)

# Define integration test constants
INTEGRATION_TEST_TIMEOUT = 30  # seconds
TEST_DATA_DIR = Path(__file__).parent / "data"

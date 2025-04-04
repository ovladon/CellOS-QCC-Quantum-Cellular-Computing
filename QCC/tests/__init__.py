"""
QCC Test Suite

This package contains test suites for the Quantum Cellular Computing (QCC) project.
It includes unit tests, integration tests, and performance benchmarks to ensure
the correct functionality and performance of the QCC system.

The test modules are organized into:
- unit: Tests for individual components
- integration: Tests for component interactions
- performance: Benchmarks for system performance
"""

import os
import sys
import logging

# Add project root to path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'tests.log'))
    ]
)

# Test environment flag
TEST_ENV = True

# Version of the test suite
__version__ = '0.1.0'

"""
Configuration module for pytest.

This file contains fixtures and setup for the QCC test suite.
"""

import os
import sys
import pytest
import asyncio
import logging
import tempfile
import shutil
from unittest.mock import Mock, patch

# Ensure the QCC package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from qcc.assembler.intent import IntentInterpreter
from qcc.assembler.security import SecurityManager
from qcc.assembler.runtime import CellRuntime
from qcc.quantum_trail import QuantumTrailManager
from qcc.common.models import Solution, Cell, CellConfiguration
from qcc.providers.repository.manager import RepositoryManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce logging noise during tests
logging.getLogger('qcc').setLevel(logging.WARNING)

# Test configuration
TEST_CONFIG = {
    "environment": "test",
    "use_mocks": True,
    "mock_providers": True,
    "mock_quantum_trail": True,
    "test_data_dir": os.path.join(os.path.dirname(__file__), 'data')
}

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def mock_intent_interpreter():
    """Create a mock intent interpreter."""
    interpreter = Mock(spec=IntentInterpreter)
    
    async def analyze_mock(user_request, context=None):
        """Mock the analyze method to return sensible defaults."""
        return {
            "intent": "test_intent",
            "confidence": 0.95,
            "required_capabilities": ["test_capability"],
            "suggested_connections": {},
            "use_previous_configurations": False
        }
    
    interpreter.analyze = analyze_mock
    return interpreter

@pytest.fixture
def mock_security_manager():
    """Create a mock security manager."""
    manager = Mock(spec=SecurityManager)
    
    async def verify_cells_mock(cells, quantum_signature):
        """Mock verify cells to always pass."""
        return True
    
    manager.verify_cells = verify_cells_mock
    return manager

@pytest.fixture
def mock_cell_runtime():
    """Create a mock cell runtime."""
    runtime = Mock(spec=CellRuntime)
    
    async def activate_cell_mock(cell):
        """Mock cell activation."""
        cell.status = "active"
        return True
    
    async def deactivate_cell_mock(cell):
        """Mock cell deactivation."""
        cell.status = "inactive"
        return True
    
    async def release_cell_mock(cell):
        """Mock cell release."""
        cell.status = "released"
        return True
    
    async def connect_cells_mock(source, target):
        """Mock cell connection."""
        return True
    
    runtime.activate_cell = activate_cell_mock
    runtime.deactivate_cell = deactivate_cell_mock
    runtime.release_cell = release_cell_mock
    runtime.connect_cells = connect_cells_mock
    
    return runtime

@pytest.fixture
def mock_quantum_trail():
    """Create a mock quantum trail manager."""
    trail = Mock(spec=QuantumTrailManager)
    
    async def generate_signature_mock(user_id, intent, context):
        """Mock signature generation."""
        return f"qt-{user_id}-{hash(str(intent))}"
    
    async def find_similar_configurations_mock(capabilities, context_similarity, max_results):
        """Mock finding similar configurations."""
        return []
    
    async def record_assembly_mock(quantum_signature, solution_id, cell_ids, connection_map, performance_metrics):
        """Mock recording assembly."""
        return True
    
    async def update_assembly_record_mock(quantum_signature, solution_id, status, performance_metrics):
        """Mock updating assembly record."""
        return True
    
    trail.generate_signature = generate_signature_mock
    trail.find_similar_configurations = find_similar_configurations_mock
    trail.record_assembly = record_assembly_mock
    trail.update_assembly_record = update_assembly_record_mock
    
    return trail

@pytest.fixture
def mock_repository_manager():
    """Create a mock repository manager."""
    manager = Mock(spec=RepositoryManager)
    
    async def get_cell_for_capability_mock(capability, parameters=None, context=None):
        """Mock getting a cell for a capability."""
        return {
            "id": f"test-cell-{capability}",
            "cell_type": f"test_type_{capability}",
            "capability": capability,
            "version": "1.0.0",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "resource_requirements": {
                "memory_mb": 10,
                "cpu_percent": 5
            }
        }
    
    manager.get_cell_for_capability = get_cell_for_capability_mock
    
    return manager

@pytest.fixture
def mock_cell():
    """Create a mock cell."""
    cell = Cell(
        id="test-cell-id",
        cell_type="test_type",
        capability="test_capability",
        version="1.0.0",
        provider="test-provider",
        quantum_signature="test-signature",
        status="initialized",
        created_at="2024-01-01T00:00:00",
        context={}
    )
    
    return cell

@pytest.fixture
def mock_solution():
    """Create a mock solution."""
    cells = {
        "test-cell-id": Cell(
            id="test-cell-id",
            cell_type="test_type",
            capability="test_capability",
            version="1.0.0",
            provider="test-provider",
            quantum_signature="test-signature",
            status="active",
            created_at="2024-01-01T00:00:00",
            context={}
        )
    }
    
    solution = Solution(
        id="test-solution-id",
        cells=cells,
        quantum_signature="test-signature",
        created_at="2024-01-01T00:00:00",
        intent={
            "intent": "test_intent",
            "required_capabilities": ["test_capability"]
        },
        status="active",
        context={}
    )
    
    return solution

@pytest.fixture
def mock_cell_configuration():
    """Create a mock cell configuration."""
    config = CellConfiguration(
        id="test-config-id",
        cell_specs=[
            {
                "cell_type": "test_type",
                "capability": "test_capability",
                "version": "1.0.0",
                "provider_url": "test-provider"
            }
        ],
        connection_map={
            "test-cell-1": ["test-cell-2"]
        },
        performance_score=0.95,
        usage_count=10,
        created_at="2024-01-01T00:00:00",
        last_used="2024-01-01T00:00:00"
    )
    
    return config

@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        "QCC_ENVIRONMENT": "test",
        "QCC_LOG_LEVEL": "WARNING",
        "QCC_TEST_MODE": "True"
    }):
        yield

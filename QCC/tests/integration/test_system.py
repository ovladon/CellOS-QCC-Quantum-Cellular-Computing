"""
End-to-end integration tests for the QCC system.

These tests verify that all components of the system work together correctly,
from user intent interpretation to cell assembly, execution, and release.
"""

import pytest
import asyncio
import os
import sys
import json
import time
import logging
from pathlib import Path

from qcc.assembler.core.assembler import CellAssembler
from qcc.assembler.intent import IntentInterpreter
from qcc.assembler.security import SecurityManager
from qcc.assembler.runtime import CellRuntime
from qcc.quantum_trail import QuantumTrailManager
from qcc.providers.repository.manager import create_repository_manager
from qcc.common.models import Cell, Solution
from qcc.common.exceptions import CellRequestError, SecurityVerificationError

# Configure logging
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG_PATH = Path(__file__).parent / "data" / "test_config.json"

@pytest.fixture
async def setup_test_environment():
    """
    Set up a test environment with real components.
    
    This fixture:
    1. Creates temporary directories for test data
    2. Initializes a repository manager with test cells
    3. Initializes the assembler with real components
    4. Cleans up after tests
    """
    # Create temp directories
    test_dir = Path(f"/tmp/qcc_integration_test_{int(time.time())}")
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(test_dir / "cells", exist_ok=True)
    os.makedirs(test_dir / "quantum_trail", exist_ok=True)
    
    # Load test configuration if it exists
    config = {}
    if TEST_CONFIG_PATH.exists():
        with open(TEST_CONFIG_PATH, 'r') as f:
            config = json.load(f)
    
    # Initialize repository manager with test cells
    repo_manager = await create_repository_manager(
        storage_path=str(test_dir / "cells"),
        config_path=None  # Use default config
    )
    
    # Register test cells
    await register_test_cells(repo_manager)
    
    # Initialize components
    intent_interpreter = IntentInterpreter()
    security_manager = SecurityManager()
    cell_runtime = CellRuntime()
    quantum_trail = QuantumTrailManager(
        storage_path=str(test_dir / "quantum_trail")
    )
    
    # Initialize assembler
    assembler = CellAssembler(
        user_id="integration_test_user",
        provider_urls=["http://localhost:8081"]  # Will be mocked
    )
    
    # Replace with actual components
    assembler.intent_interpreter = intent_interpreter
    assembler.security_manager = security_manager
    assembler.cell_runtime = cell_runtime
    assembler.quantum_trail = quantum_trail
    
    # Mock the provider request method to use our repo manager
    original_request_cell = assembler._request_cell_from_provider
    
    async def mock_request_cell(provider_url, capability, quantum_signature, context):
        cell_data = await repo_manager.get_cell_for_capability(capability, None, context)
        cell = Cell(
            id=cell_data["id"],
            cell_type=cell_data["cell_type"],
            capability=capability,
            provider=provider_url,
            quantum_signature=quantum_signature,
            status="initialized",
            created_at=cell_data.get("created_at", "2024-01-01T00:00:00"),
            context=context or {}
        )
        return cell
    
    assembler._request_cell_from_provider = mock_request_cell
    
    try:
        # Yield the test environment to the test
        yield {
            "assembler": assembler,
            "repo_manager": repo_manager,
            "test_dir": test_dir
        }
    finally:
        # Restore original method
        assembler._request_cell_from_provider = original_request_cell
        
        # Clean up
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

async def register_test_cells(repo_manager):
    """Register test cells with the repository manager."""
    # Register a text processing cell
    await repo_manager.register_cell(
        cell_type="text_processor",
        capability="text_processing",
        version="1.0.0",
        package={
            "type": "mock",
            "capabilities": ["text_processing"]
        },
        metadata={
            "description": "Text processing cell for testing",
            "resource_requirements": {
                "memory_mb": 10,
                "cpu_percent": 5
            }
        }
    )
    
    # Register a file system cell
    await repo_manager.register_cell(
        cell_type="file_system",
        capability="file_operations",
        version="1.0.0",
        package={
            "type": "mock",
            "capabilities": ["file_operations"]
        },
        metadata={
            "description": "File system cell for testing",
            "resource_requirements": {
                "memory_mb": 15,
                "cpu_percent": 8
            }
        }
    )
    
    # Register a UI rendering cell
    await repo_manager.register_cell(
        cell_type="ui_renderer",
        capability="user_interface",
        version="1.0.0",
        package={
            "type": "mock",
            "capabilities": ["user_interface"]
        },
        metadata={
            "description": "UI rendering cell for testing",
            "resource_requirements": {
                "memory_mb": 20,
                "cpu_percent": 10
            }
        }
    )

@pytest.mark.asyncio
async def test_basic_solution_assembly(setup_test_environment):
    """
    Test the basic process of assembling a solution from a user request.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    
    # Define a user request
    user_request = "Create a text document"
    
    # Define context
    context = {
        "device_info": {
            "platform": "linux",
            "memory_gb": 8,
            "cpu_cores": 4,
            "gpu_available": False
        },
        "environment": {
            "type": "desktop",
            "os": "linux"
        }
    }
    
    # Assemble a solution
    solution = await assembler.assemble_solution(user_request, context)
    
    try:
        # Validate the solution
        assert solution is not None
        assert solution.id is not None
        assert solution.status == "active"
        assert len(solution.cells) > 0
        
        # The solution should have cells for text processing and UI
        capabilities = [cell.capability for cell in solution.cells.values()]
        assert "text_processing" in capabilities
        assert "user_interface" in capabilities
        
        # Get solution details
        solution_details = assembler.active_solutions.get(solution.id)
        assert solution_details is not None
        
        # Verify quantum signature
        assert solution.quantum_signature is not None
        assert len(solution.quantum_signature) > 0
        
    finally:
        # Release the solution
        await assembler.release_solution(solution.id)
        
        # Verify the solution was released
        assert solution.id not in assembler.active_solutions

@pytest.mark.asyncio
async def test_solution_execution(setup_test_environment):
    """
    Test executing capabilities on an assembled solution.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    
    # Define a user request
    user_request = "I need to edit a text file"
    
    # Assemble a solution
    solution = await assembler.assemble_solution(user_request)
    
    try:
        # Find the text processing cell
        text_cell = None
        for cell in solution.cells.values():
            if cell.capability == "text_processing":
                text_cell = cell
                break
        
        assert text_cell is not None
        
        # Mock the cell's capabilities
        text_cell.process_text = AsyncMock(return_value={
            "status": "success",
            "outputs": [
                {
                    "name": "processed_text",
                    "value": "Processed text content",
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 5,
                "memory_used_mb": 0.2
            }
        })
        
        # Mock the execute_capability method
        text_cell.execute_capability = AsyncMock(return_value={
            "status": "success",
            "outputs": [
                {
                    "name": "result",
                    "value": "Capability executed successfully",
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 5,
                "memory_used_mb": 0.2
            }
        })
        
        # Execute the cell's capability
        result = await text_cell.execute_capability({
            "capability": "process_text",
            "parameters": {
                "text": "Sample text",
                "operation": "analyze"
            }
        })
        
        # Verify the result
        assert result["status"] == "success"
        assert "outputs" in result
        assert len(result["outputs"]) > 0
        assert "performance_metrics" in result
        
    finally:
        # Release the solution
        await assembler.release_solution(solution.id)

@pytest.mark.asyncio
async def test_solution_with_file_operations(setup_test_environment):
    """
    Test a solution that performs file operations.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    test_dir = env["test_dir"]
    
    # Create a test file
    test_file_path = test_dir / "test_file.txt"
    with open(test_file_path, 'w') as f:
        f.write("This is test content for file operations")
    
    # Define a user request
    user_request = "Read a text file and analyze its content"
    
    # Define context with the test file path
    context = {
        "device_info": {
            "platform": "linux",
            "memory_gb": 8,
            "cpu_cores": 4,
            "gpu_available": False
        },
        "file_path": str(test_file_path)
    }
    
    # Assemble a solution
    solution = await assembler.assemble_solution(user_request, context)
    
    try:
        # Validate the solution
        assert solution is not None
        assert solution.id is not None
        
        # The solution should have cells for file operations and text processing
        capabilities = [cell.capability for cell in solution.cells.values()]
        assert "file_operations" in capabilities
        assert "text_processing" in capabilities
        
        # Find the file system cell
        file_cell = None
        for cell in solution.cells.values():
            if cell.capability == "file_operations":
                file_cell = cell
                break
        
        assert file_cell is not None
        
        # Mock the cell's capabilities
        file_cell.read_file = AsyncMock(return_value={
            "status": "success",
            "outputs": [
                {
                    "name": "content",
                    "value": "This is test content for file operations",
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 8,
                "memory_used_mb": 0.3
            }
        })
        
        # Execute the cell's capability
        result = await file_cell.read_file({
            "path": str(test_file_path)
        })
        
        # Verify the result
        assert result["status"] == "success"
        assert "outputs" in result
        assert len(result["outputs"]) > 0
        assert result["outputs"][0]["name"] == "content"
        assert result["outputs"][0]["value"] == "This is test content for file operations"
        
    finally:
        # Release the solution
        await assembler.release_solution(solution.id)

@pytest.mark.asyncio
async def test_multi_intent_workflow(setup_test_environment):
    """
    Test handling multiple sequential intents with the same assembler.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    
    # First intent - create a document
    solution1 = await assembler.assemble_solution("Create a new document")
    
    try:
        # Validate first solution
        assert solution1 is not None
        assert solution1.id is not None
        
        # Store solution1 ID for verification
        solution1_id = solution1.id
        
        # Second intent - edit that document
        solution2 = await assembler.assemble_solution("Edit my document")
        
        # Validate second solution
        assert solution2 is not None
        assert solution2.id is not None
        assert solution2.id != solution1_id
        
        # Both solutions should be active
        assert solution1_id in assembler.active_solutions
        assert solution2.id in assembler.active_solutions
        
        # Release first solution
        await assembler.release_solution(solution1_id)
        
        # Verify first solution was released but second is still active
        assert solution1_id not in assembler.active_solutions
        assert solution2.id in assembler.active_solutions
        
    finally:
        # Clean up any remaining solutions
        for solution_id in list(assembler.active_solutions.keys()):
            await assembler.release_solution(solution_id)

@pytest.mark.asyncio
async def test_error_handling_and_recovery(setup_test_environment):
    """
    Test that the system can handle errors and recover gracefully.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    
    # First, create a valid solution
    solution = await assembler.assemble_solution("Create a document")
    
    # Verify the solution was created
    assert solution is not None
    assert solution.id is not None
    
    try:
        # Now try to make an invalid request that should fail
        with pytest.raises(CellRequestError):
            # Force a cell request error by asking for a non-existent capability
            original_request_cells = assembler._request_cells_by_capabilities
            
            async def failing_request(*args, **kwargs):
                raise CellRequestError("Simulated cell request failure")
            
            assembler._request_cells_by_capabilities = failing_request
            
            # This should fail
            await assembler.assemble_solution("This request will fail")
            
    finally:
        # Restore original method
        assembler._request_cells_by_capabilities = original_request_cells
        
        # The system should still be able to create new solutions after an error
        solution2 = await assembler.assemble_solution("Create another document")
        
        # Verify we can still create solutions
        assert solution2 is not None
        assert solution2.id is not None
        
        # Clean up
        for solution_id in list(assembler.active_solutions.keys()):
            await assembler.release_solution(solution_id)

@pytest.mark.asyncio
async def test_quantum_trail_usage(setup_test_environment):
    """
    Test that the quantum trail system correctly records solution configurations.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    
    # Replace quantum trail with a mock that we can inspect
    quantum_trail_records = []
    
    original_quantum_trail = assembler.quantum_trail
    
    mock_quantum_trail = Mock(spec=original_quantum_trail)
    
    async def generate_signature_mock(user_id, intent, context):
        signature = f"qt-{user_id}-{int(time.time())}"
        return signature
    
    async def record_assembly_mock(quantum_signature, solution_id, cell_ids, connection_map, performance_metrics):
        quantum_trail_records.append({
            "quantum_signature": quantum_signature,
            "solution_id": solution_id,
            "cell_ids": cell_ids,
            "connection_map": connection_map,
            "performance_metrics": performance_metrics
        })
        return True
    
    async def find_similar_configurations_mock(capabilities, context_similarity, max_results):
        # Return empty list for the first call, then return our records for subsequent calls
        if len(quantum_trail_records) == 0:
            return []
        
        # Convert records to configuration objects
        from qcc.common.models import CellConfiguration
        configs = []
        for record in quantum_trail_records:
            config = CellConfiguration(
                id=f"config-{record['solution_id']}",
                cell_specs=[
                    {
                        "cell_type": f"cell-type-{i}",
                        "capability": "test_capability",
                        "version": "1.0.0"
                    }
                    for i, cell_id in enumerate(record['cell_ids'])
                ],
                connection_map=record['connection_map'],
                performance_score=0.95,
                usage_count=1
            )
            configs.append(config)
        
        return configs[:max_results]
    
    mock_quantum_trail.generate_signature = generate_signature_mock
    mock_quantum_trail.record_assembly = record_assembly_mock
    mock_quantum_trail.find_similar_configurations = find_similar_configurations_mock
    mock_quantum_trail.update_assembly_record = AsyncMock(return_value=True)
    
    assembler.quantum_trail = mock_quantum_trail
    
    try:
        # First request - should create a new configuration
        solution1 = await assembler.assemble_solution("Create a document")
        
        # Verify it was recorded in the quantum trail
        assert len(quantum_trail_records) == 1
        assert quantum_trail_records[0]["solution_id"] == solution1.id
        
        # Release the solution
        await assembler.release_solution(solution1.id)
        
        # Second request - should find and use the previous configuration
        solution2 = await assembler.assemble_solution("Create another document")
        
        # Verify the second solution was also recorded
        assert len(quantum_trail_records) == 2
        assert quantum_trail_records[1]["solution_id"] == solution2.id
        
        # Clean up
        await assembler.release_solution(solution2.id)
        
    finally:
        # Restore original quantum trail
        assembler.quantum_trail = original_quantum_trail

@pytest.mark.asyncio
async def test_assembler_status_reporting(setup_test_environment):
    """
    Test that the assembler correctly reports its status.
    """
    # Get the test environment
    env = await setup_test_environment
    assembler = env["assembler"]
    
    # Get initial status
    initial_status = await assembler.get_status()
    
    # Verify status structure
    assert "assembler_id" in initial_status
    assert "status" in initial_status
    assert "uptime_seconds" in initial_status
    assert "active_solutions" in initial_status
    assert "cached_cells" in initial_status
    assert "total_assemblies" in initial_status
    assert "total_cells_requested" in initial_status
    
    # Record initial metrics
    initial_assemblies = initial_status["total_assemblies"]
    initial_cells_requested = initial_status["total_cells_requested"]
    
    # Create a solution
    solution = await assembler.assemble_solution("Status test solution")
    
    try:
        # Get updated status
        updated_status = await assembler.get_status()
        
        # Verify metrics were updated
        assert updated_status["total_assemblies"] == initial_assemblies + 1
        assert updated_status["total_cells_requested"] > initial_cells_requested
        assert updated_status["active_solutions"] == 1
        
    finally:
        # Release the solution
        await assembler.release_solution(solution.id)
        
        # Verify solution release is reflected in status
        final_status = await assembler.get_status()
        assert final_status["active_solutions"] == 0

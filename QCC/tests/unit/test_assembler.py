"""
Unit tests for the CellAssembler component.

These tests verify that the CellAssembler correctly interprets user intent,
requests appropriate cells, manages their lifecycle, and coordinates their
interactions.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from qcc.assembler.core.assembler import CellAssembler
from qcc.common.exceptions import CellRequestError, SecurityVerificationError
from qcc.common.models import Solution, Cell

@pytest.mark.asyncio
async def test_assembler_initialization():
    """Test that the assembler initializes correctly."""
    # Arrange
    user_id = "test_user"
    provider_urls = ["https://test-provider.org"]
    
    # Act
    assembler = CellAssembler(user_id=user_id, provider_urls=provider_urls)
    
    # Assert
    assert assembler.user_id == user_id
    assert assembler.provider_urls == provider_urls
    assert isinstance(assembler.active_solutions, dict)
    assert len(assembler.active_solutions) == 0
    assert hasattr(assembler, "intent_interpreter")
    assert hasattr(assembler, "security_manager")
    assert hasattr(assembler, "cell_runtime")
    assert hasattr(assembler, "quantum_trail")

@pytest.mark.asyncio
async def test_assemble_solution_successful(
    mock_intent_interpreter,
    mock_security_manager,
    mock_cell_runtime,
    mock_quantum_trail
):
    """Test successful solution assembly."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Replace components with mocks
    assembler.intent_interpreter = mock_intent_interpreter
    assembler.security_manager = mock_security_manager
    assembler.cell_runtime = mock_cell_runtime
    assembler.quantum_trail = mock_quantum_trail
    
    # Mock cell request
    async def mock_request_cells(*args, **kwargs):
        return {
            "cell1": Cell(
                id="cell1",
                capability="test_capability",
                provider="test_provider",
                status="initialized"
            )
        }
    
    # Patch the internal method
    with patch.object(assembler, '_request_cells_by_capabilities', new=mock_request_cells):
        # Act
        solution = await assembler.assemble_solution("Test request")
        
        # Assert
        assert solution is not None
        assert solution.id is not None
        assert len(solution.cells) == 1
        assert "cell1" in solution.cells
        assert solution.status == "active"
        
        # Verify method calls
        mock_intent_interpreter.analyze.assert_called_once()
        mock_security_manager.verify_cells.assert_called_once()
        assert mock_cell_runtime.activate_cell.call_count == 1
        mock_quantum_trail.generate_signature.assert_called_once()
        mock_quantum_trail.record_assembly.assert_called_once()

@pytest.mark.asyncio
async def test_assemble_solution_with_previous_configuration(
    mock_intent_interpreter,
    mock_security_manager,
    mock_cell_runtime,
    mock_quantum_trail,
    mock_cell_configuration
):
    """Test solution assembly using a previous configuration."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Replace components with mocks
    assembler.intent_interpreter = mock_intent_interpreter
    assembler.security_manager = mock_security_manager
    assembler.cell_runtime = mock_cell_runtime
    assembler.quantum_trail = mock_quantum_trail
    
    # Mock finding similar configurations
    async def find_similar_mock(*args, **kwargs):
        return [mock_cell_configuration]
    
    mock_quantum_trail.find_similar_configurations = find_similar_mock
    
    # Mock cell request by configuration
    async def mock_request_cells_by_configuration(*args, **kwargs):
        return {
            "cell1": Cell(
                id="cell1",
                capability="test_capability",
                provider="test_provider",
                status="initialized"
            )
        }
    
    # Patch the internal method
    with patch.object(assembler, '_request_cells_by_configuration', new=mock_request_cells_by_configuration):
        # Define a custom analysis result
        async def analyze_mock(user_request, context=None):
            return {
                "intent": "test_intent",
                "confidence": 0.95,
                "required_capabilities": ["test_capability"],
                "suggested_connections": {},
                "use_previous_configurations": True
            }
        
        mock_intent_interpreter.analyze = analyze_mock
        
        # Act
        solution = await assembler.assemble_solution("Test request")
        
        # Assert
        assert solution is not None
        assert solution.id is not None
        assert len(solution.cells) == 1
        assert "cell1" in solution.cells
        assert solution.status == "active"

@pytest.mark.asyncio
async def test_assemble_solution_cell_request_error(
    mock_intent_interpreter,
    mock_security_manager,
    mock_cell_runtime,
    mock_quantum_trail
):
    """Test error handling when cell request fails."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Replace components with mocks
    assembler.intent_interpreter = mock_intent_interpreter
    assembler.security_manager = mock_security_manager
    assembler.cell_runtime = mock_cell_runtime
    assembler.quantum_trail = mock_quantum_trail
    
    # Mock cell request to fail
    async def mock_request_cells(*args, **kwargs):
        raise CellRequestError("Failed to request cells")
    
    # Patch the internal method
    with patch.object(assembler, '_request_cells_by_capabilities', new=mock_request_cells):
        # Act & Assert
        with pytest.raises(CellRequestError):
            await assembler.assemble_solution("Test request")

@pytest.mark.asyncio
async def test_assemble_solution_security_verification_error(
    mock_intent_interpreter,
    mock_security_manager,
    mock_cell_runtime,
    mock_quantum_trail
):
    """Test error handling when security verification fails."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Replace components with mocks
    assembler.intent_interpreter = mock_intent_interpreter
    assembler.cell_runtime = mock_cell_runtime
    assembler.quantum_trail = mock_quantum_trail
    
    # Mock cell request
    async def mock_request_cells(*args, **kwargs):
        return {
            "cell1": Cell(
                id="cell1",
                capability="test_capability",
                provider="test_provider",
                status="initialized"
            )
        }
    
    # Mock security verification to fail
    security_manager = Mock()
    async def verify_cells_mock(*args, **kwargs):
        raise SecurityVerificationError("Security verification failed")
    
    security_manager.verify_cells = verify_cells_mock
    assembler.security_manager = security_manager
    
    # Patch the internal method
    with patch.object(assembler, '_request_cells_by_capabilities', new=mock_request_cells):
        # Act & Assert
        with pytest.raises(SecurityVerificationError):
            await assembler.assemble_solution("Test request")
        
        # Verify that release_cell was called to clean up
        assert mock_cell_runtime.release_cell.call_count == 1

@pytest.mark.asyncio
async def test_release_solution_successful(
    mock_solution,
    mock_cell_runtime,
    mock_quantum_trail
):
    """Test successful solution release."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Replace components with mocks
    assembler.cell_runtime = mock_cell_runtime
    assembler.quantum_trail = mock_quantum_trail
    
    # Add the solution to active solutions
    solution_id = mock_solution.id
    assembler.active_solutions[solution_id] = mock_solution
    
    # Act
    result = await assembler.release_solution(solution_id)
    
    # Assert
    assert result is True
    assert solution_id not in assembler.active_solutions
    assert mock_cell_runtime.deactivate_cell.call_count == 1
    assert mock_cell_runtime.release_cell.call_count == 1
    mock_quantum_trail.update_assembly_record.assert_called_once()

@pytest.mark.asyncio
async def test_release_solution_unknown_solution():
    """Test release of unknown solution."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    unknown_solution_id = "unknown-solution"
    
    # Act
    result = await assembler.release_solution(unknown_solution_id)
    
    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_release_solution_with_error(
    mock_solution,
    mock_cell_runtime,
    mock_quantum_trail
):
    """Test solution release when cell deactivation fails."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Replace components with mocks
    assembler.quantum_trail = mock_quantum_trail
    
    # Mock cell runtime to raise exception
    cell_runtime = Mock()
    async def deactivate_cell_mock(*args, **kwargs):
        raise RuntimeError("Failed to deactivate cell")
    
    cell_runtime.deactivate_cell = deactivate_cell_mock
    
    # Mock release cell to succeed
    async def release_cell_mock(*args, **kwargs):
        return True
    
    cell_runtime.release_cell = release_cell_mock
    
    assembler.cell_runtime = cell_runtime
    
    # Add the solution to active solutions
    solution_id = mock_solution.id
    assembler.active_solutions[solution_id] = mock_solution
    
    # Act
    result = await assembler.release_solution(solution_id)
    
    # Assert
    assert result is True
    assert solution_id not in assembler.active_solutions
    mock_quantum_trail.update_assembly_record.assert_called_once()

@pytest.mark.asyncio
async def test_select_provider_for_capability():
    """Test provider selection for capabilities."""
    # Arrange
    assembler = CellAssembler(
        user_id="test_user",
        provider_urls=["provider1", "provider2", "provider3"]
    )
    
    # Act
    provider = assembler._select_provider_for_capability("test_capability")
    
    # Assert
    assert provider in assembler.provider_urls

@pytest.mark.asyncio
async def test_select_best_configuration(mock_cell_configuration):
    """Test selection of the best configuration from alternatives."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Create configurations with different scores
    config1 = mock_cell_configuration
    config1.performance_score = 0.85
    
    config2 = mock_cell_configuration
    config2.id = "config2"
    config2.performance_score = 0.95
    
    config3 = mock_cell_configuration
    config3.id = "config3"
    config3.performance_score = 0.75
    
    configurations = [config1, config2, config3]
    
    # Act
    best_config = assembler._select_best_configuration(configurations)
    
    # Assert
    assert best_config.id == "config2"
    assert best_config.performance_score == 0.95

@pytest.mark.asyncio
async def test_request_cells_by_capabilities(mock_repository_manager):
    """Test requesting cells by capabilities."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Mock the provider selection
    def select_provider_mock(*args, **kwargs):
        return "test-provider"
    
    assembler._select_provider_for_capability = select_provider_mock
    
    # Mock the cell request
    async def request_cell_mock(*args, **kwargs):
        capability = args[1]
        return Cell(
            id=f"cell-{capability}",
            capability=capability,
            provider="test-provider",
            status="initialized"
        )
    
    assembler._request_cell_from_provider = request_cell_mock
    
    # Act
    capabilities = ["capability1", "capability2"]
    cells = await assembler._request_cells_by_capabilities(
        capabilities, 
        "test-signature",
        {"device_info": {"platform": "test"}}
    )
    
    # Assert
    assert len(cells) == 2
    assert "cell-capability1" in cells
    assert "cell-capability2" in cells
    assert cells["cell-capability1"].capability == "capability1"
    assert cells["cell-capability2"].capability == "capability2"

@pytest.mark.asyncio
async def test_get_status():
    """Test getting assembler status."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Act
    status = await assembler.get_status()
    
    # Assert
    assert "assembler_id" in status
    assert "status" in status
    assert "uptime_seconds" in status
    assert "active_solutions" in status
    assert "cached_cells" in status
    assert "total_assemblies" in status
    assert "total_cells_requested" in status
    assert status["status"] == "active"

@pytest.mark.asyncio
async def test_caching_behavior():
    """Test cell caching behavior."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Create a test cell
    test_cell = Cell(
        id="cache-test-cell",
        capability="cache-capability",
        provider="test-provider",
        status="active"
    )
    
    # Act - Add to cache
    assembler._add_to_cache(test_cell)
    cached_cell = assembler._get_from_cache("cache-capability", {})
    
    # Assert
    assert cached_cell is not None
    assert cached_cell.id == "cache-test-cell"
    
    # Test cache replacement
    newer_cell = Cell(
        id="newer-cell",
        capability="cache-capability",
        provider="test-provider",
        status="active",
        created_at="2025-01-01T00:00:00"  # Newer date
    )
    
    # Original cell has no created_at, so add one
    test_cell.created_at = "2024-01-01T00:00:00"  # Older date
    
    # Add newer cell to cache
    assembler._add_to_cache(newer_cell)
    cached_cell = assembler._get_from_cache("cache-capability", {})
    
    # Check newer cell replaced older one
    assert cached_cell.id == "newer-cell"

@pytest.mark.asyncio
async def test_request_specific_cell():
    """Test requesting a specific cell type and version."""
    # Arrange
    assembler = CellAssembler(user_id="test_user")
    
    # Parameters for the request
    provider_url = "https://test-provider.org"
    cell_type = "specific-cell-type"
    version = "1.2.3"
    quantum_signature = "test-signature"
    parameters = {"param1": "value1"}
    
    # Act
    cell = await assembler._request_specific_cell(
        provider_url,
        cell_type,
        version,
        quantum_signature,
        parameters
    )
    
    # Assert
    assert cell is not None
    assert cell.cell_type == cell_type
    assert cell.version == version
    assert cell.provider == provider_url
    assert cell.quantum_signature == quantum_signature
    assert cell.parameters == parameters

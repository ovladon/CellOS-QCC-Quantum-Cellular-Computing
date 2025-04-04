"""
Unit tests for cell functionality.

These tests verify that cells correctly implement the Cell API, handle
lifecycle events properly, and communicate with other cells as expected.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from qcc.common.models import Cell
from qcc.cells.system.file_system.main import FileSystemCell
from qcc.cells.middleware.data_visualization.main import DataVisualizationCell
from qcc.cells.application.text_editor.main import TextEditorCell
from qcc.common.exceptions import CellInitializationError, CellCapabilityError

@pytest.mark.asyncio
async def test_cell_base_initialization():
    """Test that a cell initializes correctly with basic parameters."""
    # Arrange
    cell_id = "test-cell-id"
    quantum_signature = "test-signature"
    capability = "test-capability"
    
    init_parameters = {
        "cell_id": cell_id,
        "quantum_signature": quantum_signature,
        "capability": capability,
        "context": {
            "device_info": {
                "platform": "test",
                "memory_gb": 8,
                "cpu_cores": 4,
                "gpu_available": False
            }
        }
    }
    
    # Create a generic cell model
    cell = Cell(
        id=cell_id,
        capability=capability,
        quantum_signature=quantum_signature
    )
    
    # Assert basic properties are set
    assert cell.id == cell_id
    assert cell.capability == capability
    assert cell.quantum_signature == quantum_signature
    assert cell.status == "initialized"

@pytest.mark.asyncio
async def test_file_system_cell_initialization():
    """Test that the file system cell initializes correctly."""
    # Arrange
    cell_id = "file-system-cell"
    quantum_signature = "test-signature"
    capability = "file_operations"
    
    init_parameters = {
        "cell_id": cell_id,
        "quantum_signature": quantum_signature,
        "capability": capability,
        "context": {
            "device_info": {
                "platform": "test",
                "memory_gb": 8,
                "cpu_cores": 4,
                "gpu_available": False
            },
            "security": {
                "allowed_paths": ["/tmp", "/home/test"]
            }
        },
        "configuration": {
            "read_only": False,
            "max_file_size_mb": 100
        }
    }
    
    # Act
    cell = FileSystemCell()
    result = await cell.initialize(init_parameters)
    
    # Assert
    assert result["status"] == "success"
    assert len(result["capabilities"]) > 0
    assert "file_operations" in [cap["name"] for cap in result["capabilities"]]
    assert cell.cell_id == cell_id
    assert cell.quantum_signature == quantum_signature

@pytest.mark.asyncio
async def test_file_system_cell_capabilities():
    """Test that the file system cell provides the expected capabilities."""
    # Arrange
    cell = FileSystemCell()
    await cell.initialize({
        "cell_id": "file-system-cell",
        "quantum_signature": "test-signature",
        "capability": "file_operations",
        "context": {
            "device_info": {"platform": "test"},
            "security": {"allowed_paths": ["/tmp"]}
        }
    })
    
    # Act
    list_files_params = {
        "path": "/tmp",
        "recursive": False
    }
    
    # Mock the actual file system operations
    with patch('os.listdir', return_value=["file1.txt", "file2.txt"]):
        result = await cell.list_files(list_files_params)
    
    # Assert
    assert result["status"] == "success"
    assert len(result["outputs"]) > 0
    assert result["outputs"][0]["name"] == "files"
    assert len(result["outputs"][0]["value"]) == 2
    assert "file1.txt" in result["outputs"][0]["value"]

@pytest.mark.asyncio
async def test_file_system_cell_security_constraints():
    """Test that the file system cell enforces security constraints."""
    # Arrange
    cell = FileSystemCell()
    await cell.initialize({
        "cell_id": "file-system-cell",
        "quantum_signature": "test-signature",
        "capability": "file_operations",
        "context": {
            "device_info": {"platform": "test"},
            "security": {"allowed_paths": ["/tmp"]}
        }
    })
    
    # Act - Try to access a path outside allowed paths
    list_files_params = {
        "path": "/etc",  # Not in allowed_paths
        "recursive": False
    }
    
    result = await cell.list_files(list_files_params)
    
    # Assert
    assert result["status"] == "error"
    assert "access denied" in result["outputs"][0]["value"].lower() or \
           "permission" in result["outputs"][0]["value"].lower()

@pytest.mark.asyncio
async def test_data_visualization_cell_initialization():
    """Test that the data visualization cell initializes correctly."""
    # Arrange
    cell_id = "data-viz-cell"
    quantum_signature = "test-signature"
    capability = "data_visualization"
    
    init_parameters = {
        "cell_id": cell_id,
        "quantum_signature": quantum_signature,
        "capability": capability,
        "context": {
            "device_info": {
                "platform": "test",
                "memory_gb": 8,
                "cpu_cores": 4,
                "gpu_available": True
            }
        },
        "configuration": {
            "default_theme": "light",
            "default_chart_type": "bar"
        }
    }
    
    # Act
    cell = DataVisualizationCell()
    result = await cell.initialize(init_parameters)
    
    # Assert
    assert result["status"] == "success"
    assert len(result["capabilities"]) > 0
    assert "data_visualization" in [cap["name"] for cap in result["capabilities"]]
    assert cell.cell_id == cell_id
    assert cell.configuration["default_theme"] == "light"
    assert cell.configuration["default_chart_type"] == "bar"

@pytest.mark.asyncio
async def test_data_visualization_generate_chart():
    """Test that the data visualization cell can generate charts."""
    # Arrange
    cell = DataVisualizationCell()
    await cell.initialize({
        "cell_id": "data-viz-cell",
        "quantum_signature": "test-signature",
        "capability": "data_visualization",
        "context": {"device_info": {"platform": "test"}}
    })
    
    # Act
    chart_params = {
        "chart_type": "bar",
        "data": {
            "labels": ["A", "B", "C"],
            "datasets": [{
                "label": "Dataset 1",
                "data": [10, 20, 30]
            }]
        },
        "options": {
            "title": "Test Chart"
        }
    }
    
    result = await cell.generate_chart(chart_params)
    
    # Assert
    assert result["status"] == "success"
    assert len(result["outputs"]) > 0
    assert result["outputs"][0]["name"] in ["html", "svg", "chart_data"]
    assert "performance_metrics" in result

@pytest.mark.asyncio
async def test_text_editor_cell_initialization():
    """Test that the text editor cell initializes correctly."""
    # Arrange
    cell_id = "text-editor-cell"
    quantum_signature = "test-signature"
    capability = "text_editing"
    
    init_parameters = {
        "cell_id": cell_id,
        "quantum_signature": quantum_signature,
        "capability": capability,
        "context": {
            "device_info": {
                "platform": "test",
                "memory_gb": 8,
                "cpu_cores": 4,
                "gpu_available": False
            }
        },
        "configuration": {
            "max_document_size_mb": 10,
            "auto_save": True,
            "default_font": "Arial"
        }
    }
    
    # Act
    cell = TextEditorCell()
    result = await cell.initialize(init_parameters)
    
    # Assert
    assert result["status"] == "success"
    assert len(result["capabilities"]) > 0
    assert "text_editing" in [cap["name"] for cap in result["capabilities"]]
    assert cell.cell_id == cell_id
    assert cell.configuration["auto_save"] == True

@pytest.mark.asyncio
async def test_text_editor_cell_document_operations():
    """Test text editor document operations."""
    # Arrange
    cell = TextEditorCell()
    await cell.initialize({
        "cell_id": "text-editor-cell",
        "quantum_signature": "test-signature",
        "capability": "text_editing",
        "context": {"device_info": {"platform": "test"}}
    })
    
    # Act - Create document
    create_params = {
        "name": "test.txt",
        "content": "Initial content"
    }
    
    create_result = await cell.create_document(create_params)
    
    # Assert creation result
    assert create_result["status"] == "success"
    assert create_result["outputs"][0]["name"] == "document_id"
    
    # Store document ID for next operations
    document_id = create_result["outputs"][0]["value"]
    
    # Act - Update document
    update_params = {
        "document_id": document_id,
        "content": "Updated content",
        "position": 0  # Replace from beginning
    }
    
    update_result = await cell.update_document(update_params)
    
    # Assert update result
    assert update_result["status"] == "success"
    
    # Act - Get document
    get_params = {
        "document_id": document_id
    }
    
    get_result = await cell.get_document(get_params)
    
    # Assert get result
    assert get_result["status"] == "success"
    assert get_result["outputs"][0]["name"] == "content"
    assert get_result["outputs"][0]["value"] == "Updated content"

@pytest.mark.asyncio
async def test_cell_lifecycle_events():
    """Test that cells correctly handle lifecycle events."""
    # Arrange
    cell = TextEditorCell()
    await cell.initialize({
        "cell_id": "lifecycle-test-cell",
        "quantum_signature": "test-signature",
        "capability": "text_editing",
        "context": {"device_info": {"platform": "test"}}
    })
    
    # Create a document to have some state
    await cell.create_document({
        "name": "lifecycle_test.txt",
        "content": "Test content"
    })
    
    # Act - Activate
    activate_result = await cell.activate()
    
    # Assert activation
    assert activate_result["status"] == "success"
    assert activate_result["state"] == "active"
    
    # Act - Suspend
    suspend_result = await cell.suspend()
    
    # Assert suspension
    assert suspend_result["status"] == "success"
    assert suspend_result["state"] == "suspended"
    assert "memory_snapshot_id" in suspend_result
    
    # Act - Resume
    resume_result = await cell.resume({"memory_snapshot_id": suspend_result["memory_snapshot_id"]})
    
    # Assert resumption
    assert resume_result["status"] == "success"
    assert resume_result["state"] == "active"
    
    # Act - Deactivate
    deactivate_result = await cell.deactivate()
    
    # Assert deactivation
    assert deactivate_result["status"] == "success"
    assert deactivate_result["state"] == "deactivated"
    
    # Act - Release
    release_result = await cell.release()
    
    # Assert release
    assert release_result["status"] == "success"
    assert release_result["state"] == "released"

@pytest.mark.asyncio
async def test_cell_capability_execution():
    """Test capability execution through the standard interface."""
    # Arrange
    cell = TextEditorCell()
    await cell.initialize({
        "cell_id": "capability-test-cell",
        "quantum_signature": "test-signature",
        "capability": "text_editing",
        "context": {"device_info": {"platform": "test"}}
    })
    
    # Act - Execute capability through the generic interface
    result = await cell.execute_capability({
        "capability": "create_document",
        "parameters": {
            "name": "execute_test.txt",
            "content": "Test content via generic interface"
        }
    })
    
    # Assert
    assert result["status"] == "success"
    assert "outputs" in result
    assert len(result["outputs"]) > 0
    assert result["outputs"][0]["name"] == "document_id"
    
    # Act - Try to execute non-existent capability
    invalid_result = await cell.execute_capability({
        "capability": "nonexistent_capability",
        "parameters": {}
    })
    
    # Assert error handling
    assert invalid_result["status"] == "error"
    assert "outputs" in invalid_result
    assert "error" in [output["name"] for output in invalid_result["outputs"]]

@pytest.mark.asyncio
async def test_cell_resource_management():
    """Test that cells correctly report and request resources."""
    # Arrange
    cell = DataVisualizationCell()
    await cell.initialize({
        "cell_id": "resource-test-cell",
        "quantum_signature": "test-signature",
        "capability": "data_visualization",
        "context": {"device_info": {"platform": "test"}},
        "resource_limits": {
            "max_memory_mb": 100,
            "max_cpu_percent": 50,
            "max_storage_mb": 200,
            "max_network_mbps": 10
        }
    })
    
    # Act - Get resource usage
    usage_result = await cell.get_resource_usage()
    
    # Assert resource reporting
    assert "memory" in usage_result
    assert "cpu" in usage_result
    assert "storage" in usage_result
    assert "network" in usage_result
    
    # Act - Request additional resources
    request_result = await cell.request_resources({
        "memory_mb": 50,
        "cpu_percent": 25,
        "storage_mb": 100,
        "network_mbps": 5,
        "priority": 5,
        "justification": "Processing large dataset"
    })
    
    # Assert resource request
    assert request_result["status"] in ["granted", "partial", "denied"]
    if request_result["status"] == "granted" or request_result["status"] == "partial":
        assert "granted" in request_result
        assert "memory_mb" in request_result["granted"]
        assert "cpu_percent" in request_result["granted"]

@pytest.mark.asyncio
async def test_cell_error_handling():
    """Test that cells properly handle and report errors."""
    # Arrange
    cell = FileSystemCell()
    await cell.initialize({
        "cell_id": "error-test-cell",
        "quantum_signature": "test-signature",
        "capability": "file_operations",
        "context": {
            "device_info": {"platform": "test"},
            "security": {"allowed_paths": ["/tmp"]}
        }
    })
    
    # Act - Call with invalid parameters
    result = await cell.list_files({})  # Missing required 'path' parameter
    
    # Assert
    assert result["status"] == "error"
    assert len(result["outputs"]) > 0
    assert result["outputs"][0]["name"] == "error"
    assert "path" in result["outputs"][0]["value"].lower()

@pytest.mark.asyncio
async def test_cell_communication():
    """Test that cells can communicate with each other."""
    # Arrange
    # Create both cells
    editor_cell = TextEditorCell()
    await editor_cell.initialize({
        "cell_id": "editor-cell",
        "quantum_signature": "test-signature",
        "capability": "text_editing",
        "context": {"device_info": {"platform": "test"}}
    })
    
    fs_cell = FileSystemCell()
    await fs_cell.initialize({
        "cell_id": "fs-cell",
        "quantum_signature": "test-signature",
        "capability": "file_operations",
        "context": {
            "device_info": {"platform": "test"},
            "security": {"allowed_paths": ["/tmp"]}
        }
    })
    
    # Mock connection
    editor_cell.connections = {"fs-cell": fs_cell}
    fs_cell.connections = {"editor-cell": editor_cell}
    
    # Mock call_capability method
    original_call_capability = editor_cell.call_capability
    
    async def mock_call_capability(cell_id, capability, parameters):
        if cell_id == "fs-cell" and capability == "write_file":
            return await fs_cell.write_file(parameters)
        return None
    
    editor_cell.call_capability = mock_call_capability
    
    # Act
    # Create a document in the editor
    create_result = await editor_cell.create_document({
        "name": "save_test.txt",
        "content": "Content to save"
    })
    
    document_id = create_result["outputs"][0]["value"]
    
    # Now try to save it using the file system cell
    save_result = await editor_cell.save_document({
        "document_id": document_id,
        "path": "/tmp/save_test.txt"
    })
    
    # Assert
    assert save_result["status"] == "success"
    
    # Restore original method
    editor_cell.call_capability = original_call_capability

@pytest.mark.asyncio
async def test_cell_connection_management():
    """Test that cells can manage connections to other cells."""
    # Arrange
    cell = TextEditorCell()
    await cell.initialize({
        "cell_id": "connection-test-cell",
        "quantum_signature": "test-signature",
        "capability": "text_editing",
        "context": {"device_info": {"platform": "test"}}
    })
    
    # Create a mock cell to connect to
    mock_cell = Mock()
    mock_cell.id = "mock-cell-id"
    mock_cell.capability = "mock_capability"
    
    # Act - Connect to the mock cell
    connection_result = await cell.connect_to({
        "target_cell_id": "mock-cell-id",
        "interface_name": "default",
        "connection_type": "message",
        "configuration": {}
    })
    
    # Assert connection result
    assert connection_result["status"] == "success"
    assert "connection_id" in connection_result
    
    # Store connection ID
    connection_id = connection_result["connection_id"]
    
    # Act - Get connections
    connections_result = await cell.get_connections()
    
    # Assert connections list
    assert "connections" in connections_result
    assert len(connections_result["connections"]) > 0
    
    # Act - Disconnect
    disconnect_result = await cell.disconnect(connection_id)
    
    # Assert disconnect result
    assert disconnect_result["status"] == "success"
    assert disconnect_result["connection_id"] == connection_id
    
    # Check connections again
    connections_result = await cell.get_connections()
    assert len(connections_result["connections"]) == 0

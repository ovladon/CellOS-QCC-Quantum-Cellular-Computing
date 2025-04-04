# src/cells/system/file_system/main.py

```python
"""
File system cell for the QCC architecture.

This system cell provides file system access capabilities,
allowing other cells to read, write, and manage files.
"""

import os
import asyncio
import json
import base64
from typing import Dict, List, Any, Optional, BinaryIO

from qcc.cells import BaseCell

class FileSystemCell(BaseCell):
    """
    A system cell that provides file system access capabilities.
    
    This cell enables secure, controlled access to the file system,
    allowing other cells to read, write, and manage files within
    their allowed scope.
    """
    
    def initialize(self, parameters):
        """Initialize the file system cell."""
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("read_file", self.read_file)
        self.register_capability("write_file", self.write_file)
        self.register_capability("list_directory", self.list_directory)
        self.register_capability("create_directory", self.create_directory)
        self.register_capability("delete_file", self.delete_file)
        self.register_capability("file_info", self.file_info)
        
        # Initialize working directory
        self.working_directory = parameters.get("working_directory", os.getcwd())
        
        # Initialize access permissions
        self.access_mode = parameters.get("access_mode", "read")  # read, read_write
        
        # Initialize allowed paths
        self.allowed_paths = parameters.get("allowed_paths", [self.working_directory])
        
        self.logger.info(f"File system cell initialized with ID: {self.cell_id}")
        self.logger.info(f"Working directory: {self.working_directory}")
        self.logger.info(f"Access mode: {self.access_mode}")
        
        return self.get_initialization_result()
    
    async def read_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read a file from the file system.
        
        Args:
            parameters: Dictionary containing:
                - path: Path to the file
                - encoding: Optional encoding (default: utf-8)
                - binary: Whether to return binary data (default: False)
                
        Returns:
            Dictionary containing the file content
        """
        # Validate parameters
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        path = parameters["path"]
        encoding = parameters.get("encoding", "utf-8")
        binary = parameters.get("binary", False)
        
        # Check if path is allowed
        if not self._is_path_allowed(path):
            return self._error_response(f"Access denied to path: {path}")
        
        # Check read permissions
        if self.access_mode not in ["read", "read_write"]:
            return self._error_response("File system access is restricted to write-only")
        
        try:
            # Use absolute path
            full_path = self._get_absolute_path(path)
            
            # Check if file exists
            if not os.path.isfile(full_path):
                return self._error_response(f"File not found: {path}")
            
            # Read the file
            if binary:
                with open(full_path, "rb") as f:
                    content = base64.b64encode(f.read()).decode("ascii")
                    content_type = "binary"
            else:
                with open(full_path, "r", encoding=encoding) as f:
                    content = f.read()
                    content_type = "text"
            
            # Log the operation
            self.logger.info(f"Read file: {path}")
            
            # Return the content
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "content",
                        "value": content,
                        "type": content_type
                    },
                    {
                        "name": "path",
                        "value": path,
                        "type": "string"
                    },
                    {
                        "name": "size",
                        "value": os.path.getsize(full_path),
                        "type": "number"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,  # Example value
                    "memory_used_mb": 1       # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error reading file: {str(e)}")
    
    async def write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write content to a file.
        
        Args:
            parameters: Dictionary containing:
                - path: Path to the file
                - content: Content to write
                - encoding: Optional encoding (default: utf-8)
                - binary: Whether the content is binary (default: False)
                - append: Whether to append to the file (default: False)
                
        Returns:
            Dictionary indicating success or failure
        """
        # Validate parameters
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        if "content" not in parameters:
            return self._error_response("Content parameter is required")
        
        path = parameters["path"]
        content = parameters["content"]
        encoding = parameters.get("encoding", "utf-8")
        binary = parameters.get("binary", False)
        append = parameters.get("append", False)
        
        # Check if path is allowed
        if not self._is_path_allowed(path):
            return self._error_response(f"Access denied to path: {path}")
        
        # Check write permissions
        if self.access_mode not in ["write", "read_write"]:
            return self._error_response("File system access is restricted to read-only")
        
        try:
            # Use absolute path
            full_path = self._get_absolute_path(path)
            
            # Ensure directory exists
            directory = os.path.dirname(full_path)
            os.makedirs(directory, exist_ok=True)
            
            # Write the file
            mode = "ab" if append and binary else "a" if append else "wb" if binary else "w"
            
            if binary:
                # Decode base64 content
                binary_content = base64.b64decode(content)
                with open(full_path, mode) as f:
                    f.write(binary_content)
            else:
                with open(full_path, mode, encoding=encoding) as f:
                    f.write(content)
            
            # Get file info
            file_size = os.path.getsize(full_path)
            
            # Log the operation
            self.logger.info(f"Wrote to file: {path} ({file_size} bytes)")
            
            # Return success
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "path",
                        "value": path,
                        "type": "string"
                    },
                    {
                        "name": "size",
                        "value": file_size,
                        "type": "number"
                    },
                    {
                        "name": "append",
                        "value": append,
                        "type": "boolean"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,  # Example value
                    "memory_used_mb": 1       # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error writing file: {str(e)}")
    
    async def list_directory(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        List contents of a directory.
        
        Args:
            parameters: Dictionary containing:
                - path: Path to the directory
                - pattern: Optional glob pattern
                - recursive: Whether to list recursively (default: False)
                
        Returns:
            Dictionary containing the directory contents
        """
        # Validate parameters
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        path = parameters["path"]
        pattern = parameters.get("pattern", "*")
        recursive = parameters.get("recursive", False)
        
        # Check if path is allowed
        if not self._is_path_allowed(path):
            return self._error_response(f"Access denied to path: {path}")
        
        # Check read permissions
        if self.access_mode not in ["read", "read_write"]:
            return self._error_response("File system access is restricted to write-only")
        
        try:
            # Use absolute path
            full_path = self._get_absolute_path(path)
            
            # Check if directory exists
            if not os.path.isdir(full_path):
                return self._error_response(f"Directory not found: {path}")
            
            # List directory contents
            directory_contents = []
            
            if recursive:
                # Walk the directory tree
                for root, dirs, files in os.walk(full_path):
                    # Make paths relative to the requested path
                    rel_root = os.path.relpath(root, full_path)
                    
                    # Skip the root directory itself
                    if rel_root == '.':
                        rel_path = ''
                    else:
                        rel_path = rel_root + os.sep
                    
                    for dir_name in dirs:
                        directory_contents.append({
                            "name": dir_name,
                            "path": os.path.join(rel_path, dir_name),
                            "type": "directory",
                            "size": 0
                        })
                    
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        directory_contents.append({
                            "name": file_name,
                            "path": os.path.join(rel_path, file_name),
                            "type": "file",
                            "size": os.path.getsize(file_path),
                            "modified": os.path.getmtime(file_path)
                        })
            else:
                # List only the requested directory
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    if os.path.isdir(item_path):
                        directory_contents.append({
                            "name": item,
                            "path": item,
                            "type": "directory",
                            "size": 0
                        })
                    else:
                        directory_contents.append({
                            "name": item,
                            "path": item,
                            "type": "file",
                            "size": os.path.getsize(item_path),
                            "modified": os.path.getmtime(item_path)
                        })
            
            # Apply pattern filtering
            import fnmatch
            directory_contents = [
                item for item in directory_contents
                if fnmatch.fnmatch(item["name"], pattern)
            ]
            
            # Log the operation
            self.logger.info(f"Listed directory: {path} ({len(directory_contents)} items)")
            
            # Return the directory contents
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "items",
                        "value": directory_contents,
                        "type": "array"
                    },
                    {
                        "name": "path",
                        "value": path,
                        "type": "string"
                    },
                    {
                        "name": "count",
                        "value": len(directory_contents),
                        "type": "number"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 20,  # Example value
                    "memory_used_mb": 2       # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error listing directory: {str(e)}")
    
    async def create_directory(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a directory.
        
        Args:
            parameters: Dictionary containing:
                - path: Path to the directory
                - recursive: Whether to create parent directories (default: True)
                
        Returns:
            Dictionary indicating success or failure
        """
        # Validate parameters
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        path = parameters["path"]
        recursive = parameters.get("recursive", True)
        
        # Check if path is allowed
        if not self._is_path_allowed(path):
            return self._error_response(f"Access denied to path: {path}")
        
        # Check write permissions
        if self.access_mode not in ["write", "read_write"]:
            return self._error_response("File system access is restricted to read-only")
        
        try:
            # Use absolute path
            full_path = self._get_absolute_path(path)
            
            # Create the directory
            if recursive:
                os.makedirs(full_path, exist_ok=True)
            else:
                os.mkdir(full_path)
            
            # Log the operation
            self.logger.info(f"Created directory: {path}")
            
            # Return success
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "path",
                        "value": path,
                        "type": "string"
                    },
                    {
                        "name": "created",
                        "value": True,
                        "type": "boolean"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,  # Example value
                    "memory_used_mb": 1      # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error creating directory: {str(e)}")
    
    async def delete_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete a file or directory.
        
        Args:
            parameters: Dictionary containing:
                - path: Path to the file or directory
                - recursive: Whether to recursively delete directories (default: False)
                
        Returns:
            Dictionary indicating success or failure
        """
        # Validate parameters
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        path = parameters["path"]
        recursive = parameters.get("recursive", False)
        
        # Check if path is allowed
        if not self._is_path_allowed(path):
            return self._error_response(f"Access denied to path: {path}")
        
        # Check write permissions
        if self.access_mode not in ["write", "read_write"]:
            return self._error_response("File system access is restricted to read-only")
        
        try:
            # Use absolute path
            full_path = self._get_absolute_path(path)
            
            # Check if path exists
            if not os.path.exists(full_path):
                return self._error_response(f"Path not found: {path}")
            
            # Delete file or directory
            if os.path.isdir(full_path):
                if recursive:
                    import shutil
                    shutil.rmtree(full_path)
                else:
                    os.rmdir(full_path)
            else:
                os.remove(full_path)
            
            # Log the operation
            self.logger.info(f"Deleted: {path}")
            
            # Return success
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "path",
                        "value": path,
                        "type": "string"
                    },
                    {
                        "name": "deleted",
                        "value": True,
                        "type": "boolean"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,  # Example value
                    "memory_used_mb": 1      # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error deleting: {str(e)}")
    
    async def file_info(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get information about a file or directory.
        
        Args:
            parameters: Dictionary containing:
                - path: Path to the file or directory
                
        Returns:
            Dictionary containing file or directory information
        """
        # Validate parameters
        if "path" not in parameters:
            return self._error_response("Path parameter is required")
        
        path = parameters["path"]
        
        # Check if path is allowed
        if not self._is_path_allowed(path):
            return self._error_response(f"Access denied to path: {path}")
        
        # Check read permissions
        if self.access_mode not in ["read", "read_write"]:
            return self._error_response("File system access is restricted to write-only")
        
        try:
            # Use absolute path
            full_path = self._get_absolute_path(path)
            
            # Check if path exists
            if not os.path.exists(full_path):
                return self._error_response(f"Path not found: {path}")
            
            # Get file information
            is_dir = os.path.isdir(full_path)
            file_info = {
                "name": os.path.basename(full_path),
                "path": path,
                "type": "directory" if is_dir else "file",
                "size": 0 if is_dir else os.path.getsize(full_path),
                "created": os.path.getctime(full_path),
                "modified": os.path.getmtime(full_path),
                "accessed": os.path.getatime(full_path),
                "exists": True,
                "is_directory": is_dir,
                "is_file": not is_dir
            }
            
            # Log the operation
            self.logger.info(f"Got info for: {path}")
            
            # Return file information
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "info",
                        "value": file_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 3,  # Example value
                    "memory_used_mb": 1      # Example value
                }
            }
            
        except Exception as e:
            return self._error_response(f"Error getting file info: {str(e)}")
    
    def _get_absolute_path(self, path: str) -> str:
        """
        Convert a relative path to an absolute path.
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Absolute path
        """
        if os.path.isabs(path):
            return path
        else:
            return os.path.normpath(os.path.join(self.working_directory, path))
    
    def _is_path_allowed(self, path: str) -> bool:
        """
        Check if a path is allowed based on permissions.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is allowed, False otherwise
        """
        full_path = self._get_absolute_path(path)
        
        # Check against allowed paths
        for allowed_path in self.allowed_paths:
            allowed_full_path = os.path.abspath(allowed_path)
            if full_path.startswith(allowed_full_path):
                return True
                
        return False
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
            
        Returns:
            Error response dictionary
        """
        self.logger.error(message)
        return {
            "status": "error",
            "outputs": [
                {
                    "name": "error",
                    "value": message,
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 1,
                "memory_used_mb": 0.1
            }
        }

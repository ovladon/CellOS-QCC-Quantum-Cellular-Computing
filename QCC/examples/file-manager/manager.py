"""
File Manager Cell for QCC

This cell provides basic file management capabilities within the QCC environment,
allowing users to browse, create, modify, and organize files and directories.
"""

from qcc.cells import BaseCell
from typing import Dict, List, Any, Optional
import os
import shutil
import time
import json
import logging
import base64
import mimetypes
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class FileManagerCell(BaseCell):
    """
    A cell that provides basic file management capabilities.
    
    This cell can:
    - List files and directories
    - Create files and directories
    - Delete files and directories
    - Rename files and directories
    - Copy and move files and directories
    - Read and write file contents
    - Get file metadata
    - Search for files and directories
    """
    
    def initialize(self, parameters):
        """Initialize the cell with given parameters."""
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("list_directory", self.list_directory)
        self.register_capability("create_directory", self.create_directory)
        self.register_capability("create_file", self.create_file)
        self.register_capability("delete_item", self.delete_item)
        self.register_capability("rename_item", self.rename_item)
        self.register_capability("copy_item", self.copy_item)
        self.register_capability("move_item", self.move_item)
        self.register_capability("read_file", self.read_file)
        self.register_capability("write_file", self.write_file)
        self.register_capability("get_item_info", self.get_item_info)
        self.register_capability("search_items", self.search_items)
        self.register_capability("get_file_explorer_ui", self.get_file_explorer_ui)
        
        # Initialize state
        self.state = {
            "current_directory": None,
            "bookmarks": [],
            "recent_items": [],
            "history": [],
            "history_position": -1
        }
        
        # Set up file storage
        if "root_directory" in parameters:
            self.root_directory = parameters["root_directory"]
        else:
            # Default storage location
            self.root_directory = "./data/user_files"
        
        # Create root directory if it doesn't exist
        os.makedirs(self.root_directory, exist_ok=True)
        
        # Set current directory to root
        self.state["current_directory"] = self.root_directory
        
        # Add root to history
        self._add_to_history(self.root_directory)
        
        # Load bookmarks if they exist
        self._load_bookmarks()
        
        logger.info(f"FileManagerCell initialized with ID: {self.cell_id}")
        return self.get_initialization_result()
    
    def _load_bookmarks(self):
        """Load bookmarks from storage."""
        try:
            bookmarks_path = os.path.join(self.root_directory, ".bookmarks.json")
            if os.path.exists(bookmarks_path):
                with open(bookmarks_path, 'r', encoding='utf-8') as f:
                    bookmarks = json.load(f)
                
                # Validate bookmarks
                valid_bookmarks = []
                for bookmark in bookmarks:
                    if os.path.exists(bookmark["path"]):
                        valid_bookmarks.append(bookmark)
                
                self.state["bookmarks"] = valid_bookmarks
                logger.info(f"Loaded {len(valid_bookmarks)} bookmarks")
            
        except Exception as e:
            logger.error(f"Error loading bookmarks: {e}")
    
    def _save_bookmarks(self):
        """Save bookmarks to storage."""
        try:
            bookmarks_path = os.path.join(self.root_directory, ".bookmarks.json")
            with open(bookmarks_path, 'w', encoding='utf-8') as f:
                json.dump(self.state["bookmarks"], f, indent=2)
            
            logger.info("Bookmarks saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving bookmarks: {e}")
    
    def _add_to_history(self, path):
        """Add path to navigation history."""
        # If we're not at the end of history, truncate
        if self.state["history_position"] < len(self.state["history"]) - 1:
            self.state["history"] = self.state["history"][:self.state["history_position"] + 1]
        
        # Add path to history if it's different from current
        if not self.state["history"] or self.state["history"][-1] != path:
            self.state["history"].append(path)
            
            # Limit history size
            if len(self.state["history"]) > 50:
                self.state["history"] = self.state["history"][-50:]
        
        # Update position
        self.state["history_position"] = len(self.state["history"]) - 1
    
    def _add_to_recent(self, path):
        """Add path to recent items."""
        # Add to recent items if it's a file
        if os.path.isfile(path):
            # Create recent item entry
            recent_item = {
                "path": path,
                "name": os.path.basename(path),
                "accessed_at": datetime.now().timestamp()
            }
            
            # Remove if already in list
            self.state["recent_items"] = [item for item in self.state["recent_items"] 
                                        if item["path"] != path]
            
            # Add to beginning
            self.state["recent_items"].insert(0, recent_item)
            
            # Limit size
            if len(self.state["recent_items"]) > 20:
                self.state["recent_items"] = self.state["recent_items"][:20]
    
    def _get_relative_path(self, path):
        """Convert absolute path to path relative to root directory."""
        if os.path.isabs(path):
            try:
                rel_path = os.path.relpath(path, self.root_directory)
                # Don't allow navigating outside root
                if rel_path.startswith('..'):
                    return None
                return rel_path
            except ValueError:
                return None
        return path
    
    def _get_absolute_path(self, path):
        """Convert path relative to root directory to absolute path."""
        if not os.path.isabs(path):
            abs_path = os.path.join(self.root_directory, path)
            # Normalize to prevent directory traversal attacks
            norm_path = os.path.normpath(abs_path)
            # Ensure the path is within the root directory
            if not norm_path.startswith(self.root_directory):
                return None
            return norm_path
        return path if path.startswith(self.root_directory) else None
    
    def _is_path_allowed(self, path):
        """Check if a path is within the allowed root directory."""
        abs_path = self._get_absolute_path(path)
        if not abs_path:
            return False
        
        norm_path = os.path.normpath(abs_path)
        return norm_path.startswith(self.root_directory)
    
    def _get_item_info(self, path):
        """Get detailed information about a file or directory."""
        try:
            if not self._is_path_allowed(path):
                return None
            
            abs_path = self._get_absolute_path(path)
            if not os.path.exists(abs_path):
                return None
            
            stats = os.stat(abs_path)
            
            item_info = {
                "name": os.path.basename(abs_path),
                "path": self._get_relative_path(abs_path),
                "full_path": abs_path,
                "type": "directory" if os.path.isdir(abs_path) else "file",
                "size": stats.st_size,
                "created_at": stats.st_ctime,
                "modified_at": stats.st_mtime,
                "accessed_at": stats.st_atime,
            }
            
            # Add file-specific information
            if os.path.isfile(abs_path):
                mime_type, encoding = mimetypes.guess_type(abs_path)
                item_info["mime_type"] = mime_type or "application/octet-stream"
                item_info["encoding"] = encoding
                
                # Compute hash for small files
                if stats.st_size < 10 * 1024 * 1024:  # 10MB limit
                    try:
                        with open(abs_path, 'rb') as f:
                            content = f.read()
                            item_info["md5"] = hashlib.md5(content).hexdigest()
                    except Exception:
                        pass
            
            # Add directory-specific information
            if os.path.isdir(abs_path):
                try:
                    item_info["contents_count"] = len(os.listdir(abs_path))
                except PermissionError:
                    item_info["contents_count"] = -1
            
            return item_info
            
        except Exception as e:
            logger.error(f"Error getting item info for {path}: {e}")
            return None
    
    async def list_directory(self, parameters):
        """
        List contents of a directory.
        
        Parameters:
            path (str, optional): Directory path to list, defaults to current directory
            show_hidden (bool, optional): Whether to show hidden files and directories
            sort_by (str, optional): Field to sort by (name, type, size, modified_at)
            sort_order (str, optional): Sort order (asc, desc)
            
        Returns:
            Directory contents information
        """
        try:
            # Get directory path
            directory_path = parameters.get("path")
            if not directory_path:
                directory_path = self.state["current_directory"]
            
            # Ensure path is allowed
            if not self._is_path_allowed(directory_path):
                return self._error_response(f"Access to path '{directory_path}' is not allowed")
            
            # Get absolute path
            abs_path = self._get_absolute_path(directory_path)
            if not os.path.exists(abs_path):
                return self._error_response(f"Directory '{directory_path}' does not exist")
            
            if not os.path.isdir(abs_path):
                return self._error_response(f"'{directory_path}' is not a directory")
            
            # Update current directory and history
            self.state["current_directory"] = abs_path
            self._add_to_history(abs_path)
            
            # List directory contents
            show_hidden = parameters.get("show_hidden", False)
            items = []
            
            try:
                for item_name in os.listdir(abs_path):
                    # Skip hidden items if not showing them
                    if not show_hidden and item_name.startswith('.'):
                        continue
                    
                    item_path = os.path.join(abs_path, item_name)
                    item_info = self._get_item_info(item_path)
                    
                    if item_info:
                        items.append(item_info)
            
            except PermissionError:
                return self._error_response(f"Permission denied for directory '{directory_path}'")
            
            # Sort items
            sort_by = parameters.get("sort_by", "name").lower()
            sort_order = parameters.get("sort_order", "asc").lower()
            
            valid_sort_fields = ["name", "type", "size", "modified_at", "created_at"]
            if sort_by not in valid_sort_fields:
                sort_by = "name"
            
            # Sort directories first, then by selected field
            items.sort(
                key=lambda x: (
                    0 if x["type"] == "directory" else 1,
                    x.get(sort_by, "")
                ),
                reverse=(sort_order == "desc")
            )
            
            # Get directory info
            directory_info = self._get_item_info(abs_path)
            parent_path = os.path.dirname(abs_path)
            parent_info = None
            
            # Get parent info if not at root
            if self._is_path_allowed(parent_path) and parent_path != abs_path:
                parent_info = self._get_item_info(parent_path)
            
            result = {
                "directory": directory_info,
                "parent": parent_info,
                "items": items,
                "path": self._get_relative_path(abs_path),
                "item_count": len(items)
            }
            
            logger.info(f"Listed directory: {abs_path} ({len(items)} items)")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "directory_contents",
                        "value": result,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 20,
                    "memory_used_mb": 0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            return self._error_response(f"Failed to list directory: {str(e)}")
    
    async def create_directory(self, parameters):
        """
        Create a new directory.
        
        Parameters:
            path (str): Path where to create the directory
            name (str): Name of the directory to create
            
        Returns:
            Created directory information
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
                
            if "name" not in parameters:
                return self._error_response("Name parameter is required")
            
            parent_path = parameters["path"]
            dir_name = parameters["name"]
            
            # Ensure valid name
            if not dir_name or '/' in dir_name or '\\' in dir_name:
                return self._error_response("Invalid directory name")
            
            # Ensure path is allowed
            if not self._is_path_allowed(parent_path):
                return self._error_response(f"Access to path '{parent_path}' is not allowed")
            
            # Get absolute path
            abs_parent_path = self._get_absolute_path(parent_path)
            if not os.path.exists(abs_parent_path):
                return self._error_response(f"Parent directory '{parent_path}' does not exist")
            
            if not os.path.isdir(abs_parent_path):
                return self._error_response(f"'{parent_path}' is not a directory")
            
            # Create new directory path
            new_dir_path = os.path.join(abs_parent_path, dir_name)
            
            # Check if already exists
            if os.path.exists(new_dir_path):
                return self._error_response(f"Directory '{dir_name}' already exists")
            
            # Create directory
            os.makedirs(new_dir_path)
            
            # Get info about new directory
            dir_info = self._get_item_info(new_dir_path)
            
            logger.info(f"Created directory: {new_dir_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "directory",
                        "value": dir_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 10,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating directory: {e}")
            return self._error_response(f"Failed to create directory: {str(e)}")
    
    async def create_file(self, parameters):
        """
        Create a new file.
        
        Parameters:
            path (str): Path where to create the file
            name (str): Name of the file to create
            content (str, optional): Initial content of the file
            
        Returns:
            Created file information
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
                
            if "name" not in parameters:
                return self._error_response("Name parameter is required")
            
            parent_path = parameters["path"]
            file_name = parameters["name"]
            content = parameters.get("content", "")
            
            # Ensure valid name
            if not file_name or '/' in file_name or '\\' in file_name:
                return self._error_response("Invalid file name")
            
            # Ensure path is allowed
            if not self._is_path_allowed(parent_path):
                return self._error_response(f"Access to path '{parent_path}' is not allowed")
            
            # Get absolute path
            abs_parent_path = self._get_absolute_path(parent_path)
            if not os.path.exists(abs_parent_path):
                return self._error_response(f"Parent directory '{parent_path}' does not exist")
            
            if not os.path.isdir(abs_parent_path):
                return self._error_response(f"'{parent_path}' is not a directory")
            
            # Create new file path
            new_file_path = os.path.join(abs_parent_path, file_name)
            
            # Check if already exists
            if os.path.exists(new_file_path):
                return self._error_response(f"File '{file_name}' already exists")
            
            # Create file with initial content
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get info about new file
            file_info = self._get_item_info(new_file_path)
            
            # Add to recent items
            self._add_to_recent(new_file_path)
            
            logger.info(f"Created file: {new_file_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "file",
                        "value": file_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return self._error_response(f"Failed to create file: {str(e)}")
    
    async def delete_item(self, parameters):
        """
        Delete a file or directory.
        
        Parameters:
            path (str): Path to the item to delete
            recursive (bool, optional): Whether to delete directories recursively
            
        Returns:
            Deletion status
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
            
            item_path = parameters["path"]
            recursive = parameters.get("recursive", False)
            
            # Ensure path is allowed
            if not self._is_path_allowed(item_path):
                return self._error_response(f"Access to path '{item_path}' is not allowed")
            
            # Get absolute path
            abs_item_path = self._get_absolute_path(item_path)
            if not os.path.exists(abs_item_path):
                return self._error_response(f"Item '{item_path}' does not exist")
            
            # Get item info before deletion
            item_info = self._get_item_info(abs_item_path)
            
            # Delete directory
            if os.path.isdir(abs_item_path):
                # Check if directory is empty or recursive is enabled
                is_empty = len(os.listdir(abs_item_path)) == 0
                
                if not is_empty and not recursive:
                    return self._error_response(f"Directory '{item_path}' is not empty. Use recursive=true to delete.")
                
                try:
                    if recursive:
                        shutil.rmtree(abs_item_path)
                    else:
                        os.rmdir(abs_item_path)
                except PermissionError:
                    return self._error_response(f"Permission denied for directory '{item_path}'")
            
            # Delete file
            elif os.path.isfile(abs_item_path):
                try:
                    os.remove(abs_item_path)
                except PermissionError:
                    return self._error_response(f"Permission denied for file '{item_path}'")
            
            # Remove from recent items if present
            self.state["recent_items"] = [item for item in self.state["recent_items"] 
                                         if item["path"] != abs_item_path]
            
            # Remove from bookmarks if present
            self.state["bookmarks"] = [bookmark for bookmark in self.state["bookmarks"] 
                                      if bookmark["path"] != abs_item_path]
            self._save_bookmarks()
            
            logger.info(f"Deleted item: {abs_item_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "result",
                        "value": {
                            "deleted": True,
                            "item": item_info
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 20,
                    "memory_used_mb": 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"Error deleting item: {e}")
            return self._error_response(f"Failed to delete item: {str(e)}")
    
    async def rename_item(self, parameters):
        """
        Rename a file or directory.
        
        Parameters:
            path (str): Path to the item to rename
            new_name (str): New name for the item
            
        Returns:
            Renamed item information
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
                
            if "new_name" not in parameters:
                return self._error_response("New name parameter is required")
            
            item_path = parameters["path"]
            new_name = parameters["new_name"]
            
            # Ensure valid name
            if not new_name or '/' in new_name or '\\' in new_name:
                return self._error_response("Invalid name")
            
            # Ensure path is allowed
            if not self._is_path_allowed(item_path):
                return self._error_response(f"Access to path '{item_path}' is not allowed")
            
            # Get absolute path
            abs_item_path = self._get_absolute_path(item_path)
            if not os.path.exists(abs_item_path):
                return self._error_response(f"Item '{item_path}' does not exist")
            
            # Create new path
            parent_dir = os.path.dirname(abs_item_path)
            new_path = os.path.join(parent_dir, new_name)
            
            # Check if target already exists
            if os.path.exists(new_path):
                return self._error_response(f"Item '{new_name}' already exists")
            
            # Rename the item
            try:
                os.rename(abs_item_path, new_path)
            except PermissionError:
                return self._error_response(f"Permission denied for renaming '{item_path}'")
            
            # Get info about renamed item
            renamed_info = self._get_item_info(new_path)
            
            # Update recent items if present
            for item in self.state["recent_items"]:
                if item["path"] == abs_item_path:
                    item["path"] = new_path
                    item["name"] = new_name
            
            # Update bookmarks if present
            for bookmark in self.state["bookmarks"]:
                if bookmark["path"] == abs_item_path:
                    bookmark["path"] = new_path
                    bookmark["name"] = new_name
            self._save_bookmarks()
            
            logger.info(f"Renamed {abs_item_path} to {new_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "item",
                        "value": renamed_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": 0.2
                }
            }
            
        except Exception as e:
            logger.error(f"Error renaming item: {e}")
            return self._error_response(f"Failed to rename item: {str(e)}")
    
    async def copy_item(self, parameters):
        """
        Copy a file or directory.
        
        Parameters:
            source_path (str): Path to the item to copy
            destination_path (str): Path where to copy the item
            recursive (bool, optional): Whether to copy directories recursively
            
        Returns:
            Copied item information
        """
        try:
            if "source_path" not in parameters:
                return self._error_response("Source path parameter is required")
                
            if "destination_path" not in parameters:
                return self._error_response("Destination path parameter is required")
            
            source_path = parameters["source_path"]
            destination_path = parameters["destination_path"]
            recursive = parameters.get("recursive", True)
            
            # Ensure paths are allowed
            if not self._is_path_allowed(source_path):
                return self._error_response(f"Access to source path '{source_path}' is not allowed")
                
            if not self._is_path_allowed(destination_path):
                return self._error_response(f"Access to destination path '{destination_path}' is not allowed")
            
            # Get absolute paths
            abs_source_path = self._get_absolute_path(source_path)
            abs_destination_path = self._get_absolute_path(destination_path)
            
            if not os.path.exists(abs_source_path):
                return self._error_response(f"Source item '{source_path}' does not exist")
                
            if not os.path.exists(abs_destination_path):
                return self._error_response(f"Destination path '{destination_path}' does not exist")
                
            if not os.path.isdir(abs_destination_path):
                return self._error_response(f"Destination '{destination_path}' is not a directory")
            
            # Get source item name and create target path
            source_name = os.path.basename(abs_source_path)
            target_path = os.path.join(abs_destination_path, source_name)
            
            # Check if target already exists
            if os.path.exists(target_path):
                return self._error_response(f"Item '{source_name}' already exists in destination")
            
            # Copy the item
            try:
                if os.path.isdir(abs_source_path):
                    if recursive:
                        shutil.copytree(abs_source_path, target_path)
                    else:
                        # Create directory without contents
                        os.makedirs(target_path)
                else:
                    shutil.copy2(abs_source_path, target_path)
            except PermissionError:
                return self._error_response(f"Permission denied for copying '{source_path}'")
            
            # Get info about copied item
            copied_info = self._get_item_info(target_path)
            
            logger.info(f"Copied {abs_source_path} to {target_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "item",
                        "value": copied_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 30,
                    "memory_used_mb": 0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Error copying item: {e}")
            return self._error_response(f"Failed to copy item: {str(e)}")
    
    async def move_item(self, parameters):
        """
        Move a file or directory.
        
        Parameters:
            source_path (str): Path to the item to move
            destination_path (str): Path where to move the item
            
        Returns:
            Moved item information
        """
        try:
            if "source_path" not in parameters:
                return self._error_response("Source path parameter is required")
                
            if "destination_path" not in parameters:
                return self._error_response("Destination path parameter is required")
            
            source_path = parameters["source_path"]
            destination_path = parameters["destination_path"]
            
            # Ensure paths are allowed
            if not self._is_path_allowed(source_path):
                return self._error_response(f"Access to source path '{source_path}' is not allowed")
                
            if not self._is_path_allowed(destination_path):
                return self._error_response(f"Access to destination path '{destination_path}' is not allowed")
            
            # Get absolute paths
            abs_source_path = self._get_absolute_path(source_path)
            abs_destination_path = self._get_absolute_path(destination_path)
            
            if not os.path.exists(abs_source_path):
                return self._error_response(f"Source item '{source_path}' does not exist")
                
            if not os.path.exists(abs_destination_path):
                return self._error_response(f"Destination path '{destination_path}' does not exist")
                
            if not os.path.isdir(abs_destination_path):
                return self._error_response(f"Destination '{destination_path}' is not a directory")
            
            # Get source item name and create target path
            source_name = os.path.basename(abs_source_path)
            target_path = os.path.join(abs_destination_path, source_name)
            
            # Check if target already exists
            if os.path.exists(target_path):
                return self._error_response(f"Item '{source_name}' already exists in destination")
            
            # Move the item
            try:
                shutil.move(abs_source_path, target_path)
            except PermissionError:
                return self._error_response(f"Permission denied for moving '{source_path}'")
            
            # Get info about moved item
            moved_info = self._get_item_info(target_path)
            
            # Update recent items if present
            for item in self.state["recent_items"]:
                if item["path"] == abs_source_path:
                    item["path"] = target_path
            
            # Update bookmarks if present
            for bookmark in self.state["bookmarks"]:
                if bookmark["path"] == abs_source_path:
                    bookmark["path"] = target_path
            self._save_bookmarks()
            
            logger.info(f"Moved {abs_source_path} to {target_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "item",
                        "value": moved_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 25,
                    "memory_used_mb": 0.4
                }
            }
            
        except Exception as e:
            logger.error(f"Error moving item: {e}")
            return self._error_response(f"Failed to move item: {str(e)}")
    
    async def read_file(self, parameters):
        """
        Read the contents of a file.
        
        Parameters:
            path (str): Path to the file to read
            encoding (str, optional): File encoding (default: utf-8)
            as_base64 (bool, optional): Whether to return binary files as base64
            
        Returns:
            File contents
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
            
            file_path = parameters["path"]
            encoding = parameters.get("encoding", "utf-8")
            as_base64 = parameters.get("as_base64", False)
            
            # Ensure path is allowed
            if not self._is_path_allowed(file_path):
                return self._error_response(f"Access to path '{file_path}' is not allowed")
            
            # Get absolute path
            abs_file_path = self._get_absolute_path(file_path)
            if not os.path.exists(abs_file_path):
                return self._error_response(f"File '{file_path}' does not exist")
            
            if not os.path.isfile(abs_file_path):
                return self._error_response(f"'{file_path}' is not a file")
            
            # Get file info
            file_info = self._get_item_info(abs_file_path)
            
            # Check if file is binary
            mime_type = file_info.get("mime_type", "")
            is_binary = not (
                mime_type.startswith("text/") or 
                mime_type in ["application/json", "application/xml", "application/javascript"]
            )
            
            # Read file content
            try:
                if is_binary or as_base64:
                    with open(abs_file_path, 'rb') as f:
                        content = f.read()
                        content_base64 = base64.b64encode(content).decode('ascii')
                        file_content = {
                            "content": content_base64,
                            "encoding": "base64",
                            "binary": True,
                            "size": len(content)
                        }
                else:
                    with open(abs_file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        file_content = {
                            "content": content,
                            "encoding": encoding,
                            "binary": False,
                            "size": len(content)
                        }
            except UnicodeDecodeError:
                # If we get a decode error, read as binary and encode as base64
                with open(abs_file_path, 'rb') as f:
                    content = f.read()
                    content_base64 = base64.b64encode(content).decode('ascii')
                    file_content = {
                        "content": content_base64,
                        "encoding": "base64",
                        "binary": True,
                        "size": len(content)
                    }
            except PermissionError:
                return self._error_response(f"Permission denied for file '{file_path}'")
            
            # Add to recent items
            self._add_to_recent(abs_file_path)
            
            logger.info(f"Read file: {abs_file_path} (size: {file_content['size']} bytes)")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "file_content",
                        "value": file_content,
                        "type": "object"
                    },
                    {
                        "name": "file_info",
                        "value": file_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 20,
                    "memory_used_mb": file_content['size'] / (1024 * 1024)
                }
            }
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return self._error_response(f"Failed to read file: {str(e)}")
    
    async def write_file(self, parameters):
        """
        Write content to a file.
        
        Parameters:
            path (str): Path to the file to write
            content (str or base64 string): Content to write
            encoding (str, optional): File encoding for text content (default: utf-8)
            is_base64 (bool, optional): Whether the content is base64 encoded
            mode (str, optional): Write mode (write, append)
            
        Returns:
            Updated file information
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
                
            if "content" not in parameters:
                return self._error_response("Content parameter is required")
            
            file_path = parameters["path"]
            content = parameters["content"]
            encoding = parameters.get("encoding", "utf-8")
            is_base64 = parameters.get("is_base64", False)
            mode = parameters.get("mode", "write")
            
            # Ensure path is allowed
            if not self._is_path_allowed(file_path):
                return self._error_response(f"Access to path '{file_path}' is not allowed")
            
            # Get absolute path
            abs_file_path = self._get_absolute_path(file_path)
            
            # Check if parent directory exists
            parent_dir = os.path.dirname(abs_file_path)
            if not os.path.exists(parent_dir):
                return self._error_response(f"Parent directory does not exist")
            
            # Determine write mode
            file_mode = "w" if mode == "write" else "a"
            
            # Write file content
            try:
                if is_base64:
                    # Decode base64 content and write as binary
                    try:
                        binary_content = base64.b64decode(content)
                    except Exception:
                        return self._error_response("Invalid base64 content")
                    
                    with open(abs_file_path, file_mode + "b") as f:
                        f.write(binary_content)
                else:
                    # Write as text
                    with open(abs_file_path, file_mode, encoding=encoding) as f:
                        f.write(content)
            except PermissionError:
                return self._error_response(f"Permission denied for file '{file_path}'")
            
            # Get updated file info
            file_info = self._get_item_info(abs_file_path)
            
            # Add to recent items
            self._add_to_recent(abs_file_path)
            
            logger.info(f"Wrote to file: {abs_file_path} (mode: {mode})")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "file",
                        "value": file_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 15,
                    "memory_used_mb": len(content) / (1024 * 1024) if isinstance(content, str) else 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Error writing file: {e}")
            return self._error_response(f"Failed to write file: {str(e)}")
    
    async def get_item_info(self, parameters):
        """
        Get information about a file or directory.
        
        Parameters:
            path (str): Path to the item
            
        Returns:
            Item information
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
            
            item_path = parameters["path"]
            
            # Ensure path is allowed
            if not self._is_path_allowed(item_path):
                return self._error_response(f"Access to path '{item_path}' is not allowed")
            
            # Get absolute path
            abs_item_path = self._get_absolute_path(item_path)
            if not os.path.exists(abs_item_path):
                return self._error_response(f"Item '{item_path}' does not exist")
            
            # Get item info
            item_info = self._get_item_info(abs_item_path)
            
            # Add to recent items if it's a file
            if os.path.isfile(abs_item_path):
                self._add_to_recent(abs_item_path)
            
            logger.info(f"Got info for item: {abs_item_path}")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "item_info",
                        "value": item_info,
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 5,
                    "memory_used_mb": 0.1
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting item info: {e}")
            return self._error_response(f"Failed to get item info: {str(e)}")
    
    async def search_items(self, parameters):
        """
        Search for files and directories.
        
        Parameters:
            path (str): Root path to search in
            query (str): Search query
            recursive (bool, optional): Whether to search recursively
            file_types (list, optional): File types to include in search
            include_hidden (bool, optional): Whether to include hidden files
            max_results (int, optional): Maximum number of results to return
            
        Returns:
            Search results
        """
        try:
            if "path" not in parameters:
                return self._error_response("Path parameter is required")
                
            if "query" not in parameters:
                return self._error_response("Query parameter is required")
            
            root_path = parameters["path"]
            query = parameters["query"].lower()
            recursive = parameters.get("recursive", True)
            file_types = parameters.get("file_types", [])
            include_hidden = parameters.get("include_hidden", False)
            max_results = parameters.get("max_results", 100)
            
            # Ensure path is allowed
            if not self._is_path_allowed(root_path):
                return self._error_response(f"Access to path '{root_path}' is not allowed")
            
            # Get absolute path
            abs_root_path = self._get_absolute_path(root_path)
            if not os.path.exists(abs_root_path):
                return self._error_response(f"Path '{root_path}' does not exist")
            
            if not os.path.isdir(abs_root_path):
                return self._error_response(f"'{root_path}' is not a directory")
            
            # Prepare file types
            if file_types:
                file_types = [f.lower() for f in file_types]
            
            # Search for files
            results = []
            
            try:
                if recursive:
                    for root, dirs, files in os.walk(abs_root_path):
                        # Skip hidden directories if not included
                        if not include_hidden:
                            dirs[:] = [d for d in dirs if not d.startswith('.')]
                        
                        # Skip paths outside allowed root
                        if not self._is_path_allowed(root):
                            dirs[:] = []
                            continue
                        
                        # Check directories
                        for dir_name in dirs:
                            if len(results) >= max_results:
                                break
                                
                            if query in dir_name.lower():
                                dir_path = os.path.join(root, dir_name)
                                item_info = self._get_item_info(dir_path)
                                if item_info:
                                    results.append(item_info)
                        
                        # Check files
                        for file_name in files:
                            if len(results) >= max_results:
                                break
                                
                            # Skip hidden files if not included
                            if not include_hidden and file_name.startswith('.'):
                                continue
                                
                            # Check file name matches
                            if query in file_name.lower():
                                file_path = os.path.join(root, file_name)
                                
                                # Check file extension if file types specified
                                if file_types:
                                    ext = os.path.splitext(file_name)[1].lower()
                                    if ext[1:] not in file_types:  # Remove dot from extension
                                        continue
                                
                                item_info = self._get_item_info(file_path)
                                if item_info:
                                    results.append(item_info)
                else:
                    # Non-recursive search, just look in the top directory
                    items = os.listdir(abs_root_path)
                    
                    for item_name in items:
                        if len(results) >= max_results:
                            break
                            
                        # Skip hidden items if not included
                        if not include_hidden and item_name.startswith('.'):
                            continue
                            
                        # Check name matches
                        if query in item_name.lower():
                            item_path = os.path.join(abs_root_path, item_name)
                            
                            # Check file extension if file types specified and it's a file
                            if file_types and os.path.isfile(item_path):
                                ext = os.path.splitext(item_name)[1].lower()
                                if ext[1:] not in file_types:  # Remove dot from extension
                                    continue
                            
                            item_info = self._get_item_info(item_path)
                            if item_info:
                                results.append(item_info)
            
            except PermissionError:
                return self._error_response(f"Permission denied for directory '{root_path}'")
            
            logger.info(f"Search results for '{query}' in {abs_root_path}: {len(results)} items")
            
            return {
                "status": "success",
                "outputs": [
                    {
                        "name": "search_results",
                        "value": {
                            "query": query,
                            "root_path": self._get_relative_path(abs_root_path),
                            "results": results,
                            "count": len(results),
                            "truncated": len(results) >= max_results
                        },
                        "type": "object"
                    }
                ],
                "performance_metrics": {
                    "execution_time_ms": 50,
                    "memory_used_mb": 0.5
                }
            }
            
        except Exception as e:
            logger.error(f"Error searching items: {e}")
            return self._error_response(f"Failed to search items: {str(e)}")
    
    async def get_file_explorer_ui(self, parameters=None):
        """
        Get a file explorer UI.
        
        Parameters:
            path (str, optional): Initial path to display
            
        Returns:
            HTML UI for file exploration
        """
        # Determine initial path
        initial_path = None
        if parameters and "path" in parameters:
            path = parameters["path"]
            if self._is_path_allowed(path):
                abs_path = self._get_absolute_path(path)
                if os.path.exists(abs_path) and os.path.isdir(abs_path):
                    initial_path = self._get_relative_path(abs_path)
        
        if not initial_path:
            initial_path = self._get_relative_path(self.state["current_directory"])
        
        # Generate bookmarks HTML
        bookmarks_html = ""
        for bookmark in self.state["bookmarks"]:
            bookmark_name = bookmark["name"]
            bookmark_path = self._get_relative_path(bookmark["path"])
            bookmarks_html += f"""
            <div class="bookmark-item" data-path="{bookmark_path}" onclick="navigateTo('{bookmark_path}')">
                <span class="bookmark-icon">📂</span>
                <span class="bookmark-name">{bookmark_name}</span>
            </div>
            """
        
        # Generate HTML UI
        html = f"""
        <div class="file-explorer">
            <div class="explorer-header">
                <div class="navigation-controls">
                    <button id="back-btn" onclick="navigateBack()" title="Back">◀</button>
                    <button id="forward-btn" onclick="navigateForward()" title="Forward">▶</button>
                    <button id="up-btn" onclick="navigateUp()" title="Up">▲</button>
                    <button id="refresh-btn" onclick="refreshDirectory()" title="Refresh">🔄</button>
                </div>
                <div class="path-input-container">
                    <input type="text" id="path-input" value="{initial_path}" placeholder="Path">
                    <button onclick="navigateToInput()">Go</button>
                </div>
                <div class="view-controls">
                    <button onclick="toggleHiddenFiles()" id="hidden-toggle" title="Show hidden files">👁️</button>
                    <select id="sort-select" onchange="changeSort()">
                        <option value="name">Name</option>
                        <option value="type">Type</option>
                        <option value="size">Size</option>
                        <option value="modified_at">Modified</option>
                        <option value="created_at">Created</option>
                    </select>
                    <select id="order-select" onchange="changeSort()">
                        <option value="asc">Ascending</option>
                        <option value="desc">Descending</option>
                    </select>
                </div>
            </div>
            
            <div class="explorer-content">
                <div class="sidebar">
                    <div class="sidebar-section">
                        <div class="sidebar-header">Bookmarks</div>
                        <div class="bookmark-list" id="bookmark-list">
                            {bookmarks_html}
                        </div>
                    </div>
                    <div class="sidebar-section">
                        <div class="sidebar-header">Recent Files</div>
                        <div class="recent-list" id="recent-list">
                            <!-- Recent files will be loaded here -->
                        </div>
                    </div>
                </div>
                
                <div class="main-content">
                    <div class="directory-contents" id="directory-contents">
                        <div class="loading">Loading...</div>
                    </div>
                </div>
            </div>
            
            <div class="explorer-footer">
                <div id="status-bar">Ready</div>
                <div id="selection-info"></div>
            </div>
            
            <!-- Context Menu -->
            <div id="context-menu" class="context-menu">
                <div class="context-menu-item" data-action="open">Open</div>
                <div class="context-menu-item" data-action="bookmark">Add to Bookmarks</div>
                <div class="context-menu-item" data-action="rename">Rename</div>
                <div class="context-menu-item" data-action="copy">Copy</div>
                <div class="context-menu-item" data-action="move">Move/Cut</div>
                <div class="context-menu-item" data-action="delete">Delete</div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item" data-action="new-file">New File</div>
                <div class="context-menu-item" data-action="new-folder">New Folder</div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item" data-action="properties">Properties</div>
            </div>
            
            <!-- Dialog Templates -->
            <div id="rename-dialog" class="dialog hidden">
                <div class="dialog-content">
                    <div class="dialog-header">
                        <h4>Rename</h4>
                        <span class="dialog-close" onclick="closeDialog('rename-dialog')">&times;</span>
                    </div>
                    <div class="dialog-body">
                        <label for="rename-input">New Name:</label>
                        <input type="text" id="rename-input">
                    </div>
                    <div class="dialog-footer">
                        <button onclick="confirmRename()">Rename</button>
                        <button onclick="closeDialog('rename-dialog')">Cancel</button>
                    </div>
                </div>
            </div>
            
            <div id="new-item-dialog" class="dialog hidden">
                <div class="dialog-content">
                    <div class="dialog-header">
                        <h4 id="new-item-title">New Item</h4>
                        <span class="dialog-close" onclick="closeDialog('new-item-dialog')">&times;</span>
                    </div>
                    <div class="dialog-body">
                        <label for="new-item-input">Name:</label>
                        <input type="text" id="new-item-input">
                    </div>
                    <div class="dialog-footer">
                        <button onclick="confirmNewItem()">Create</button>
                        <button onclick="closeDialog('new-item-dialog')">Cancel</button>
                    </div>
                </div>
            </div>
            
            <div id="properties-dialog" class="dialog hidden">
                <div class="dialog-content properties-dialog-content">
                    <div class="dialog-header">
                        <h4>Properties</h4>
                        <span class="dialog-close" onclick="closeDialog('properties-dialog')">&times;</span>
                    </div>
                    <div class="dialog-body properties-body" id="properties-body">
                        <!-- Properties will be loaded here -->
                    </div>
                    <div class="dialog-footer">
                        <button onclick="closeDialog('properties-dialog')">Close</button>
                    </div>
                </div>
            </div>
            
            <div id="confirmation-dialog" class="dialog hidden">
                <div class="dialog-content">
                    <div class="dialog-header">
                        <h4 id="confirmation-title">Confirm</h4>
                        <span class="dialog-close" onclick="closeDialog('confirmation-dialog')">&times;</span>
                    </div>
                    <div class="dialog-body">
                        <p id="confirmation-message">Are you sure?</p>
                    </div>
                    <div class="dialog-footer">
                        <button id="confirmation-confirm" onclick="closeDialog('confirmation-dialog')">Yes</button>
                        <button onclick="closeDialog('confirmation-dialog')">Cancel</button>
                    </div>
                </div>
            </div>
        </div>
        
        <style>
            .file-explorer {
                display: flex;
                flex-direction: column;
                height: 600px;
                border: 1px solid #ccc;
                border-radius: 4px;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            
            .explorer-header {
                display: flex;
                padding: 8px;
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
                gap: 8px;
            }
            
            .navigation-controls {
                display: flex;
                gap: 4px;
            }
            
            .navigation-controls button {
                width: 30px;
                height: 30px;
                padding: 0;
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 4px;
                cursor: pointer;
            }
            
            .path-input-container {
                flex: 1;
                display: flex;
                gap: 4px;
            }
            
            .path-input-container input {
                flex: 1;
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            
            .path-input-container button {
                padding: 0 8px;
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 4px;
                cursor: pointer;
            }
            
            .view-controls {
                display: flex;
                gap: 4px;
            }
            
            .view-controls button, .view-controls select {
                padding: 4px 8px;
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 4px;
            }
            
            .explorer-content {
                display: flex;
                flex: 1;
                overflow: hidden;
            }
            
            .sidebar {
                width: 200px;
                border-right: 1px solid #ddd;
                display: flex;
                flex-direction: column;
                overflow-y: auto;
            }
            
            .sidebar-section {
                margin-bottom: 16px;
            }
            
            .sidebar-header {
                padding: 8px;
                font-weight: bold;
                background-color: #f9f9f9;
                border-bottom: 1px solid #eee;
            }
            
            .bookmark-list, .recent-list {
                display: flex;
                flex-direction: column;
            }
            
            .bookmark-item, .recent-item {
                padding: 6px 8px;
                display: flex;
                align-items: center;
                gap: 8px;
                cursor: pointer;
                border-bottom: 1px solid #f5f5f5;
            }
            
            .bookmark-item:hover, .recent-item:hover {
                background-color: #f5f5f5;
            }
            
            .bookmark-icon, .recent-icon {
                font-size: 16px;
            }
            
            .bookmark-name, .recent-name {
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            
            .main-content {
                flex: 1;
                overflow-y: auto;
                background-color: white;
            }
            
            .directory-contents {
                display: flex;
                flex-direction: column;
            }
            
            .item-row {
                display: flex;
                padding: 8px;
                border-bottom: 1px solid #f5f5f5;
                align-items: center;
                cursor: pointer;
            }
            
            .item-row:hover {
                background-color: #f5f5f5;
            }
            
            .item-row.selected {
                background-color: #e3f2fd;
            }
            
            .item-icon {
                margin-right: 8px;
                font-size: 18px;
                width: 24px;
                text-align: center;
            }
            
            .item-name {
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            
            .item-details {
                display: flex;
                gap: 16px;
                color: #666;
                font-size: 0.9em;
            }
            
            .item-size, .item-date {
                white-space: nowrap;
            }
            
            .explorer-footer {
                padding: 4px 8px;
                background-color: #f5f5f5;
                border-top: 1px solid #ddd;
                display: flex;
                justify-content: space-between;
            }
            
            #status-bar {
                font-size: 0.9em;
                color: #666;
            }
            
            #selection-info {
                font-size: 0.9em;
                color: #666;
            }
            
            .loading {
                padding: 32px;
                text-align: center;
                color: #666;
            }
            
            .empty-directory {
                padding: 32px;
                text-align: center;
                color: #666;
            }
            
            .context-menu {
                position: absolute;
                display: none;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                padding: 4px 0;
                z-index: 1000;
            }
            
            .context-menu-item {
                padding: 8px 16px;
                cursor: pointer;
            }
            
            .context-menu-item:hover {
                background-color: #f5f5f5;
            }
            
            .context-menu-separator {
                height: 1px;
                background-color: #eee;
                margin: 4px 0;
            }
            
            .dialog {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 2000;
            }
            
            .dialog.hidden {
                display: none;
            }
            
            .dialog-content {
                background-color: white;
                border-radius: 4px;
                width: 400px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            }
            
            .properties-dialog-content {
                width: 500px;
            }
            
            .dialog-header {
                padding: 12px 16px;
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .dialog-header h4 {
                margin: 0;
            }
            
            .dialog-close {
                font-size: 20px;
                cursor: pointer;
                color: #666;
            }
            
            .dialog-body {
                padding: 16px;
            }
            
            .properties-body {
                max-height: 400px;
                overflow-y: auto;
            }
            
            .dialog-body label {
                display: block;
                margin-bottom: 8px;
            }
            
            .dialog-body input {
                width: 100%;
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-bottom: 16px;
            }
            
            .dialog-footer {
                padding: 12px 16px;
                background-color: #f5f5f5;
                border-top: 1px solid #ddd;
                display: flex;
                justify-content: flex-end;
                gap: 8px;
            }
            
            .dialog-footer button {
                padding: 6px 12px;
                border: 1px solid #ccc;
                background-color: white;
                border-radius: 4px;
                cursor: pointer;
            }
            
            .dialog-footer button:first-child {
                background-color: #4F46E5;
                color: white;
                border-color: #4F46E5;
            }
            
            .property-row {
                display: flex;
                margin-bottom: 8px;
                padding-bottom: 8px;
                border-bottom: 1px solid #eee;
            }
            
            .property-name {
                font-weight: bold;
                width: 120px;
                flex-shrink: 0;
            }
            
            .property-value {
                flex: 1;
                word-break: break-word;
            }
            
            .hidden {
                display: none;
            }
        </style>
        
        <script>
            // State
            let currentPath = "{initial_path}";
            let showHiddenFiles = false;
            let sortBy = "name";
            let sortOrder = "asc";
            let selectedItems = [];
            let clipboardData = null;
            let clipboardOperation = null;
            let historyPosition = {self.state["history_position"]};
            let history = {json.dumps(self.state["history"])};
            
            // Initialize on load
            document.addEventListener('DOMContentLoaded', function() {
                loadDirectory(currentPath);
                loadRecentFiles();
                
                // Setup events
                setupContextMenu();
                setupDragAndDrop();
                
                // Setup keyboard shortcuts
                document.addEventListener('keydown', handleKeyboard);
                
                // Setup path input
                const pathInput = document.getElementById('path-input');
                pathInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        navigateToInput();
                    }
                });
                
                // Update navigation buttons
                updateNavigationButtons();
            });
            
            // Load directory contents
            async function loadDirectory(path, updateHistory = true) {
                const contentsElement = document.getElementById('directory-contents');
                contentsElement.innerHTML = '<div class="loading">Loading...</div>';
                
                updateStatus(`Loading ${path}...`);
                
                try {
                    const response = await callCapability('list_directory', {
                        path: path,
                        show_hidden: showHiddenFiles,
                        sort_by: sortBy,
                        sort_order: sortOrder
                    });
                    
                    if (response.status === 'success') {
                        const directoryContents = response.outputs[0].value;
                        
                        // Update current path
                        currentPath = directoryContents.path;
                        document.getElementById('path-input').value = currentPath;
                        
                        // Add to history if requested
                        if (updateHistory) {
                            addToHistory(path);
                        }
                        
                        // Clear selection
                        selectedItems = [];
                        updateSelectionInfo();
                        
                        // Render items
                        renderDirectoryContents(directoryContents);
                        
                        updateStatus(`${directoryContents.items.length} items`);
                    } else {
                        contentsElement.innerHTML = `<div class="error">Error: ${response.outputs[0].value}</div>`;
                        updateStatus('Error loading directory');
                    }
                } catch (error) {
                    contentsElement.innerHTML = `<div class="error">Error: ${error.message}</div>`;
                    updateStatus('Error loading directory');
                }
            }
            
            // Render directory contents
            function renderDirectoryContents(directoryContents) {
                const contentsElement = document.getElementById('directory-contents');
                contentsElement.innerHTML = '';
                
                if (directoryContents.items.length === 0) {
                    contentsElement.innerHTML = '<div class="empty-directory">This folder is empty</div>';
                    return;
                }
                
                // Add parent directory if available
                if (directoryContents.parent) {
                    const parentRow = document.createElement('div');
                    parentRow.className = 'item-row';
                    parentRow.dataset.path = directoryContents.parent.path;
                    parentRow.dataset.type = 'directory';
                    parentRow.dataset.name = '..';
                    
                    parentRow.innerHTML = `
                        <div class="item-icon">📁</div>
                        <div class="item-name">..</div>
                        <div class="item-details">
                            <div class="item-size">Parent Directory</div>
                            <div class="item-date"></div>
                        </div>
                    `;
                    
                    parentRow.addEventListener('click', (e) => {
                        navigateTo(directoryContents.parent.path);
                    });
                    
                    contentsElement.appendChild(parentRow);
                }
                
                // Add items
                directoryContents.items.forEach(item => {
                    const itemRow = document.createElement('div');
                    itemRow.className = 'item-row';
                    itemRow.dataset.path = item.path;
                    itemRow.dataset.type = item.type;
                    itemRow.dataset.name = item.name;
                    
                    const icon = item.type === 'directory' ? '📁' : getFileIcon(item.name);
                    const size = item.type === 'directory' ? 
                        (item.contents_count >= 0 ? `${item.contents_count} items` : 'Unknown') : 
                        formatFileSize(item.size);
                    const date = new Date(item.modified_at * 1000).toLocaleString();
                    
                    itemRow.innerHTML = `
                        <div class="item-icon">${icon}</div>
                        <div class="item-name">${item.name}</div>
                        <div class="item-details">
                            <div class="item-size">${size}</div>
                            <div class="item-date">${date}</div>
                        </div>
                    `;
                    
                    // Add click handler
                    itemRow.addEventListener('click', (e) => {
                        if (e.ctrlKey) {
                            toggleItemSelection(itemRow);
                        } else if (e.shiftKey && selectedItems.length > 0) {
                            handleShiftSelection(itemRow);
                        } else {
                            if (!itemRow.classList.contains('selected')) {
                                clearSelection();
                                selectItem(itemRow);
                            }
                            
                            // Open on double-click
                            if (e.detail === 2) {
                                openItem(item.path, item.type);
                            }
                        }
                    });
                    
                    // Add context menu
                    itemRow.addEventListener('contextmenu', (e) => {
                        e.preventDefault();
                        
                        if (!itemRow.classList.contains('selected')) {
                            clearSelection();
                            selectItem(itemRow);
                        }
                        
                        showContextMenu(e, item);
                    });
                    
                    contentsElement.appendChild(itemRow);
                });
                
                // Add empty area context menu
                contentsElement.addEventListener('contextmenu', (e) => {
                    // Only show if clicking on the container itself, not an item
                    if (e.target === contentsElement) {
                        e.preventDefault();
                        clearSelection();
                        showDirectoryContextMenu(e);
                    }
                });
            }
            
            // Navigation functions
            function navigateTo(path) {
                loadDirectory(path);
            }
            
            function navigateToInput() {
                const path = document.getElementById('path-input').value;
                navigateTo(path);
            }
            
            function navigateUp() {
                const pathParts = currentPath.split('/');
                if (pathParts.length > 1) {
                    pathParts.pop();
                    const parentPath = pathParts.join('/') || '/';
                    navigateTo(parentPath);
                }
            }
            
            function navigateBack() {
                if (historyPosition > 0) {
                    historyPosition--;
                    navigateTo(history[historyPosition], false);
                }
                updateNavigationButtons();
            }
            
            function navigateForward() {
                if (historyPosition < history.length - 1) {
                    historyPosition++;
                    navigateTo(history[historyPosition], false);
                }
                updateNavigationButtons();
            }
            
            function refreshDirectory() {
                loadDirectory(currentPath, false);
            }
            
            function addToHistory(path) {
                // If we're not at the end of history, truncate
                if (historyPosition < history.length - 1) {
                    history = history.slice(0, historyPosition + 1);
                }
                
                // Add path to history if it's different from current
                if (history.length === 0 || history[history.length - 1] !== path) {
                    history.push(path);
                    
                    // Limit history size
                    if (history.length > 50) {
                        history = history.slice(-50);
                    }
                }
                
                // Update position
                historyPosition = history.length - 1;
                
                // Update navigation buttons
                updateNavigationButtons();
            }
            
            function updateNavigationButtons() {
                document.getElementById('back-btn').disabled = historyPosition <= 0;
                document.getElementById('forward-btn').disabled = historyPosition >= history.length - 1;
            }
            
            // Item operations
            function openItem(path, type) {
                if (type === 'directory') {
                    navigateTo(path);
                } else {
                    openFile(path);
                }
            }
            
            async function openFile(path) {
                updateStatus(`Opening ${path}...`);
                
                try {
                    const response = await callCapability('read_file', {
                        path: path
                    });
                    
                    if (response.status === 'success') {
                        const fileContent = response.outputs[0].value;
                        updateStatus(`Opened ${path}`);
                        
                        // In a real implementation, this would open the file in an editor cell
                        alert(`File content loaded (${fileContent.size} bytes)`);
                    } else {
                        updateStatus('Error opening file');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error opening file');
                    alert(`Error: ${error.message}`);
                }
            }
            
            async function createNewFile() {
                showDialog('new-item-dialog');
                document.getElementById('new-item-title').textContent = 'New File';
                document.getElementById('new-item-input').value = 'New File.txt';
                
                // Store the type for later use
                document.getElementById('new-item-dialog').dataset.type = 'file';
            }
            
            async function createNewFolder() {
                showDialog('new-item-dialog');
                document.getElementById('new-item-title').textContent = 'New Folder';
                document.getElementById('new-item-input').value = 'New Folder';
                
                // Store the type for later use
                document.getElementById('new-item-dialog').dataset.type = 'directory';
            }
            
            async function confirmNewItem() {
                const name = document.getElementById('new-item-input').value;
                if (!name) {
                    alert('Please enter a name');
                    return;
                }
                
                const type = document.getElementById('new-item-dialog').dataset.type;
                closeDialog('new-item-dialog');
                
                if (type === 'file') {
                    await createFile(name);
                } else {
                    await createDirectory(name);
                }
            }
            
            async function createFile(name) {
                updateStatus(`Creating file ${name}...`);
                
                try {
                    const response = await callCapability('create_file', {
                        path: currentPath,
                        name: name,
                        content: ''
                    });
                    
                    if (response.status === 'success') {
                        updateStatus(`Created file ${name}`);
                        refreshDirectory();
                    } else {
                        updateStatus('Error creating file');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error creating file');
                    alert(`Error: ${error.message}`);
                }
            }
            
            async function createDirectory(name) {
                updateStatus(`Creating directory ${name}...`);
                
                try {
                    const response = await callCapability('create_directory', {
                        path: currentPath,
                        name: name
                    });
                    
                    if (response.status === 'success') {
                        updateStatus(`Created directory ${name}`);
                        refreshDirectory();
                    } else {
                        updateStatus('Error creating directory');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error creating directory');
                    alert(`Error: ${error.message}`);
                }
            }
            
            async function renameSelectedItem() {
                if (selectedItems.length !== 1) {
                    alert('Please select exactly one item to rename');
                    return;
                }
                
                const itemElement = selectedItems[0];
                const itemPath = itemElement.dataset.path;
                const itemName = itemElement.dataset.name;
                
                showDialog('rename-dialog');
                document.getElementById('rename-input').value = itemName;
                document.getElementById('rename-dialog').dataset.path = itemPath;
            }
            
            async function confirmRename() {
                const newName = document.getElementById('rename-input').value;
                if (!newName) {
                    alert('Please enter a name');
                    return;
                }
                
                const path = document.getElementById('rename-dialog').dataset.path;
                closeDialog('rename-dialog');
                
                updateStatus(`Renaming to ${newName}...`);
                
                try {
                    const response = await callCapability('rename_item', {
                        path: path,
                        new_name: newName
                    });
                    
                    if (response.status === 'success') {
                        updateStatus(`Renamed to ${newName}`);
                        refreshDirectory();
                    } else {
                        updateStatus('Error renaming item');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error renaming item');
                    alert(`Error: ${error.message}`);
                }
            }
            
            async function deleteSelectedItems() {
                if (selectedItems.length === 0) {
                    alert('Please select items to delete');
                    return;
                }
                
                const itemCount = selectedItems.length;
                const isDirectory = selectedItems[0].dataset.type === 'directory';
                
                showConfirmationDialog(
                    'Confirm Delete',
                    `Are you sure you want to delete ${itemCount} ${itemCount === 1 ? 'item' : 'items'}?`,
                    async () => {
                        for (const item of selectedItems) {
                            await deleteItem(item.dataset.path);
                        }
                        refreshDirectory();
                    }
                );
            }
            
            async function deleteItem(path) {
                updateStatus(`Deleting ${path}...`);
                
                try {
                    const response = await callCapability('delete_item', {
                        path: path,
                        recursive: true
                    });
                    
                    if (response.status === 'success') {
                        updateStatus(`Deleted ${path}`);
                    } else {
                        updateStatus('Error deleting item');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error deleting item');
                    alert(`Error: ${error.message}`);
                }
            }
            
            function copySelectedItems() {
                if (selectedItems.length === 0) {
                    alert('Please select items to copy');
                    return;
                }
                
                clipboardData = selectedItems.map(item => ({
                    path: item.dataset.path,
                    type: item.dataset.type,
                    name: item.dataset.name
                }));
                
                clipboardOperation = 'copy';
                
                updateStatus(`${selectedItems.length} items copied to clipboard`);
            }
            
            function cutSelectedItems() {
                if (selectedItems.length === 0) {
                    alert('Please select items to cut');
                    return;
                }
                
                clipboardData = selectedItems.map(item => ({
                    path: item.dataset.path,
                    type: item.dataset.type,
                    name: item.dataset.name
                }));
                
                clipboardOperation = 'cut';
                
                updateStatus(`${selectedItems.length} items cut to clipboard`);
            }
            
            async function pasteItems() {
                if (!clipboardData || clipboardData.length === 0) {
                    alert('Nothing to paste');
                    return;
                }
                
                const operation = clipboardOperation;
                
                for (const item of clipboardData) {
                    if (operation === 'copy') {
                        await copyItem(item.path, currentPath);
                    } else if (operation === 'cut') {
                        await moveItem(item.path, currentPath);
                    }
                }
                
                // Clear clipboard if this was a cut operation
                if (operation === 'cut') {
                    clipboardData = null;
                    clipboardOperation = null;
                }
                
                refreshDirectory();
            }
            
            async function copyItem(sourcePath, destinationPath) {
                updateStatus(`Copying ${sourcePath}...`);
                
                try {
                    const response = await callCapability('copy_item', {
                        source_path: sourcePath,
                        destination_path: destinationPath,
                        recursive: true
                    });
                    
                    if (response.status === 'success') {
                        updateStatus(`Copied ${sourcePath}`);
                    } else {
                        updateStatus('Error copying item');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error copying item');
                    alert(`Error: ${error.message}`);
                }
            }
            
            async function moveItem(sourcePath, destinationPath) {
                updateStatus(`Moving ${sourcePath}...`);
                
                try {
                    const response = await callCapability('move_item', {
                        source_path: sourcePath,
                        destination_path: destinationPath
                    });
                    
                    if (response.status === 'success') {
                        updateStatus(`Moved ${sourcePath}`);
                    } else {
                        updateStatus('Error moving item');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error moving item');
                    alert(`Error: ${error.message}`);
                }
            }
            
            async function showItemProperties() {
                if (selectedItems.length !== 1) {
                    alert('Please select exactly one item to view properties');
                    return;
                }
                
                const itemElement = selectedItems[0];
                const itemPath = itemElement.dataset.path;
                
                updateStatus(`Loading properties for ${itemPath}...`);
                
                try {
                    const response = await callCapability('get_item_info', {
                        path: itemPath
                    });
                    
                    if (response.status === 'success') {
                        const itemInfo = response.outputs[0].value;
                        updateStatus(`Loaded properties for ${itemPath}`);
                        showPropertiesDialog(itemInfo);
                    } else {
                        updateStatus('Error loading properties');
                        alert(`Error: ${response.outputs[0].value}`);
                    }
                } catch (error) {
                    updateStatus('Error loading properties');
                    alert(`Error: ${error.message}`);
                }
            }
            
            function showPropertiesDialog(itemInfo) {
                const propertiesBody = document.getElementById('properties-body');
                propertiesBody.innerHTML = '';
                
                // Basic properties
                addProperty(propertiesBody, 'Name', itemInfo.name);
                addProperty(propertiesBody, 'Type', itemInfo.type.charAt(0).toUpperCase() + itemInfo.type.slice(1));
                addProperty(propertiesBody, 'Path', itemInfo.path);
                addProperty(propertiesBody, 'Size', formatFileSize(itemInfo.size));
                
                // Dates
                addProperty(propertiesBody, 'Created', new Date(itemInfo.created_at * 1000).toLocaleString());
                addProperty(propertiesBody, 'Modified', new Date(itemInfo.modified_at * 1000).toLocaleString());
                addProperty(propertiesBody, 'Accessed', new Date(itemInfo.accessed_at * 1000).toLocaleString());
                
                // Type-specific properties
                if (itemInfo.type === 'directory') {
                    addProperty(propertiesBody, 'Contents', itemInfo.contents_count >= 0 ? 
                        `${itemInfo.contents_count} items` : 'Unknown');
                } else {
                    addProperty(propertiesBody, 'MIME Type', itemInfo.mime_type || 'Unknown');
                    if (itemInfo.encoding) {
                        addProperty(propertiesBody, 'Encoding', itemInfo.encoding);
                    }
                    if (itemInfo.md5) {
                        addProperty(propertiesBody, 'MD5 Hash', itemInfo.md5);
                    }
                }
                
                showDialog('properties-dialog');
            }
            
            function addProperty(container, name, value) {
                const row = document.createElement('div');
                row.className = 'property-row';
                
                const nameElement = document.createElement('div');
                nameElement.className = 'property-name';
                nameElement.textContent = name;
                
                const valueElement = document.createElement('div');
                valueElement.className = 'property-value';
                valueElement.textContent = value !== undefined && value !== null ? value : 'N/A';
                
                row.appendChild(nameElement);
                row.appendChild(valueElement);
                container.appendChild(row);
            }
            
            async function addToBookmarks() {
                if (selectedItems.length !== 1) {
                    alert('Please select exactly one item to bookmark');
                    return;
                }
                
                const itemElement = selectedItems[0];
                const itemPath = itemElement.dataset.path;
                const itemName = itemElement.dataset.name;
                const itemType = itemElement.dataset.type;
                
                // Only allow bookmarking directories
                if (itemType !== 'directory') {
                    alert('Only directories can be bookmarked');
                    return;
                }
                
                // Add bookmark
                try {
                    // In a real implementation, this would call a capability
                    // Here we'll just update the UI
                    const bookmarkList = document.getElementById('bookmark-list');
                    const bookmarkItem = document.createElement('div');
                    bookmarkItem.className = 'bookmark-item';
                    bookmarkItem.dataset.path = itemPath;
                    bookmarkItem.innerHTML = `
                        <span class="bookmark-icon">📂</span>
                        <span class="bookmark-name">${itemName}</span>
                    `;
                    
                    bookmarkItem.addEventListener('click', () => {
                        navigateTo(itemPath);
                    });
                    
                    bookmarkList.appendChild(bookmarkItem);
                    
                    updateStatus(`Added ${itemName} to bookmarks`);
                } catch (error) {
                    updateStatus('Error adding bookmark');
                    alert(`Error: ${error.message}`);
                }
            }
            
            // Selection handling
            function selectItem(itemElement) {
                itemElement.classList.add('selected');
                selectedItems.push(itemElement);
                updateSelectionInfo();
            }
            
            function toggleItemSelection(itemElement) {
                if (itemElement.classList.contains('selected')) {
                    itemElement.classList.remove('selected');
                    selectedItems = selectedItems.filter(item => item !== itemElement);
                } else {
                    itemElement.classList.add('selected');
                    selectedItems.push(itemElement);
                }
                updateSelectionInfo();
            }
            
            function handleShiftSelection(itemElement) {
                const allItems = Array.from(document.querySelectorAll('.item-row'));
                const lastSelectedIndex = allItems.indexOf(selectedItems[selectedItems.length - 1]);
                const currentIndex = allItems.indexOf(itemElement);
                
                clearSelection();
                
                // Select all items between last selected and current
                const start = Math.min(lastSelectedIndex, currentIndex);
                const end = Math.max(lastSelectedIndex, currentIndex);
                
                for (let i = start; i <= end; i++) {
                    selectItem(allItems[i]);
                }
            }
            
            function clearSelection() {
                selectedItems.forEach(item => {
                    item.classList.remove('selected');
                });
                selectedItems = [];
                updateSelectionInfo();
            }
            
            function updateSelectionInfo() {
                const selectionInfo = document.getElementById('selection-info');
                
                if (selectedItems.length === 0) {
                    selectionInfo.textContent = '';
                } else {
                    selectionInfo.textContent = `${selectedItems.length} item(s) selected`;
                }
            }
            
            // Context menu
            function setupContextMenu() {
                const menu = document.getElementById('context-menu');
                
                // Close menu on outside click
                document.addEventListener('click', () => {
                    menu.style.display = 'none';
                });
            }
            
            function showContextMenu(event, item) {
                const menu = document.getElementById('context-menu');
                const menuItems = menu.querySelectorAll('.context-menu-item');
                
                // Configure menu based on item type
                menuItems.forEach(menuItem => {
                    const action = menuItem.dataset.action;
                    
                    // Handle directory-specific items
                    if (item.type !== 'directory' && action === 'bookmark') {
                        menuItem.style.display = 'none';
                    } else {
                        menuItem.style.display = 'block';
                    }
                    
                    // Add click listeners
                    menuItem.onclick = () => handleContextMenuAction(action);
                });
                
                // Position menu
                menu.style.left = `${event.clientX}px`;
                menu.style.top = `${event.clientY}px`;
                menu.style.display = 'block';
            }
            
            function showDirectoryContextMenu(event) {
                const menu = document.getElementById('context-menu');
                const menuItems = menu.querySelectorAll('.context-menu-item');
                
                // Configure menu for directory background
                menuItems.forEach(menuItem => {
                    const action = menuItem.dataset.action;
                    
                    // Only show new file/folder options
                    if (['new-file', 'new-folder', 'properties'].includes(action)) {
                        menuItem.style.display = 'block';
                    } else if (action === 'paste' && clipboardData && clipboardData.length > 0) {
                        menuItem.style.display = 'block';
                    } else {
                        menuItem.style.display = 'none';
                    }
                    
                    // Add click listeners
                    menuItem.onclick = () => handleContextMenuAction(action);
                });
                
                // Position menu
                menu.style.left = `${event.clientX}px`;
                menu.style.top = `${event.clientY}px`;
                menu.style.display = 'block';
            }
            
            function handleContextMenuAction(action) {
                // Hide menu
                document.getElementById('context-menu').style.display = 'none';
                
                // Handle action
                switch (action) {
                    case 'open':
                        if (selectedItems.length === 1) {
                            openItem(selectedItems[0].dataset.path, selectedItems[0].dataset.type);
                        }
                        break;
                    case 'bookmark':
                        addToBookmarks();
                        break;
                    case 'rename':
                        renameSelectedItem();
                        break;
                    case 'copy':
                        copySelectedItems();
                        break;
                    case 'move':
                        cutSelectedItems();
                        break;
                    case 'paste':
                        pasteItems();
                        break;
                    case 'delete':
                        deleteSelectedItems();
                        break;
                    case 'new-file':
                        createNewFile();
                        break;
                    case 'new-folder':
                        createNewFolder();
                        break;
                    case 'properties':
                        showItemProperties();
                        break;
                }
            }
            
            // Dialog management
            function showDialog(dialogId) {
                document.getElementById(dialogId).classList.remove('hidden');
                
                // Focus first input if present
                const input = document.querySelector(`#${dialogId} input`);
                if (input) {
                    setTimeout(() => {
                        input.focus();
                        input.select();
                    }, 100);
                }
            }
            
            function closeDialog(dialogId) {
                document.getElementById(dialogId).classList.add('hidden');
            }
            
            function showConfirmationDialog(title, message, confirmCallback) {
                document.getElementById('confirmation-title').textContent = title;
                document.getElementById('confirmation-message').textContent = message;
                
                const confirmButton = document.getElementById('confirmation-confirm');
                confirmButton.onclick = () => {
                    closeDialog('confirmation-dialog');
                    confirmCallback();
                };
                
                showDialog('confirmation-dialog');
            }
            
            // Utility functions
            function toggleHiddenFiles() {
                showHiddenFiles = !showHiddenFiles;
                document.getElementById('hidden-toggle').innerText = showHiddenFiles ? '👁️‍🗨️' : '👁️';
                refreshDirectory();
            }
            
            function changeSort() {
                sortBy = document.getElementById('sort-select').value;
                sortOrder = document.getElementById('order-select').value;
                refreshDirectory();
            }
            
            function updateStatus(message) {
                document.getElementById('status-bar').textContent = message;
            }
            
            function formatFileSize(bytes) {
                if (bytes === 0) return '0 B';
                
                const k = 1024;
                const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
            
            function getFileIcon(filename) {
                const ext = filename.split('.').pop().toLowerCase();
                
                // Text files
                if (['txt', 'md', 'rtf', 'log', 'ini', 'cfg'].includes(ext)) {
                    return '📄';
                }
                
                // Code files
                if (['py', 'js', 'html', 'css', 'java', 'c', 'cpp', 'h', 'json', 'xml'].includes(ext)) {
                    return '📝';
                }
                
                // Image files
                if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'].includes(ext)) {
                    return '🖼️';
                }
                
                // Document files
                if (['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'pdf'].includes(ext)) {
                    return '📰';
                }
                
                // Audio files
                if (['mp3', 'wav', 'ogg', 'flac', 'm4a'].includes(ext)) {
                    return '🎵';
                }
                
                // Video files
                if (['mp4', 'avi', 'mov', 'wmv', 'webm', 'flv'].includes(ext)) {
                    return '🎬';
                }
                
                // Archive files
                if (['zip', 'rar', 'tar', 'gz', '7z'].includes(ext)) {
                    return '📦';
                }
                
                // Default icon
                return '📄';
            }
            
            // Setup drag and drop
            function setupDragAndDrop() {
                const directoryContents = document.getElementById('directory-contents');
                
                // In a real implementation, this would handle actual file uploads
                // Here we're just demonstrating the UI behavior
                
                directoryContents.addEventListener('dragover', (event) => {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = 'copy';
                    directoryContents.classList.add('drag-over');
                });
                
                directoryContents.addEventListener('dragleave', () => {
                    directoryContents.classList.remove('drag-over');
                });
                
                directoryContents.addEventListener('drop', (event) => {
                    event.preventDefault();
                    directoryContents.classList.remove('drag-over');
                    
                    // In a real implementation, this would handle file uploads
                    alert('File upload not implemented in this example');
                });
            }
            
            // Keyboard shortcuts
            function handleKeyboard(event) {
                // Ignore if in input field
                if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                    return;
                }
                
                // Navigation
                if (event.key === 'Backspace') {
                    navigateUp();
                    event.preventDefault();
                }
                
                // Selection
                if (event.key === 'a' && (event.ctrlKey || event.metaKey)) {
                    // Select all items
                    clearSelection();
                    document.querySelectorAll('.item-row').forEach(item => {
                        // Skip parent directory
                        if (item.dataset.name !== '..') {
                            selectItem(item);
                        }
                    });
                    event.preventDefault();
                }
                
                // Delete
                if (event.key === 'Delete' && selectedItems.length > 0) {
                    deleteSelectedItems();
                    event.preventDefault();
                }
                
                // Copy/Cut/Paste
                if (event.ctrlKey || event.metaKey) {
                    if (event.key === 'c' && selectedItems.length > 0) {
                        copySelectedItems();
                        event.preventDefault();
                    } else if (event.key === 'x' && selectedItems.length > 0) {
                        cutSelectedItems();
                        event.preventDefault();
                    } else if (event.key === 'v' && clipboardData && clipboardData.length > 0) {
                        pasteItems();
                        event.preventDefault();
                    }
                }
                
                // Rename
                if (event.key === 'F2' && selectedItems.length === 1) {
                    renameSelectedItem();
                    event.preventDefault();
                }
                
                // Refresh
                if (event.key === 'F5') {
                    refreshDirectory();
                    event.preventDefault();
                }
            }
            
            // Recent files
            async function loadRecentFiles() {
                // In a real implementation, this would call a capability
                // Here we'll simulate it with placeholder data
                const recentList = document.getElementById('recent-list');
                recentList.innerHTML = '';
                
                // Add some placeholder recent items
                const placeholders = [
                    { name: 'Document.txt', path: 'documents/Document.txt', icon: '📄' },
                    { name: 'Image.png', path: 'pictures/Image.png', icon: '🖼️' },
                    { name: 'Presentation.pptx', path: 'documents/Presentation.pptx', icon: '📰' }
                ];
                
                placeholders.forEach(item => {
                    const itemElement = document.createElement('div');
                    itemElement.className = 'recent-item';
                    itemElement.dataset.path = item.path;
                    
                    itemElement.innerHTML = `
                        <div class="recent-icon">${item.icon}</div>
                        <div class="recent-name">${item.name}</div>
                    `;
                    
                    itemElement.addEventListener('click', () => {
                        // In a real implementation, this would navigate to the file's directory
                        // and select it, or open it directly
                        alert(`Would open: ${item.path}`);
                    });
                    
                    recentList.appendChild(itemElement);
                });
            }
            
            // Call capability wrapper
            async function callCapability(capability, params = {}) {
                // This function would normally communicate with the QCC assembler
                // For this example, we'll simulate it using a mock function
                
                // In a real implementation, this would be replaced with actual HTTP calls
                // to the assembler's API
                const response = await window.qcc.executeCapability(
                    '{self.cell_id}', 
                    capability, 
                    params
                );
                
                return response;
            }
        </script>
        """
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "html",
                    "value": html,
                    "type": "string",
                    "format": "html"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 50,
                "memory_used_mb": 1.0
            }
        }
    
    def _error_response(self, message):
        """Create an error response with the provided message."""
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
    
    async def suspend(self):
        """Prepare for suspension by saving state."""
        # Save bookmarks
        self._save_bookmarks()
        
        # Return suspension result with state
        return {
            "status": "success",
            "state": self.state
        }
    
    async def resume(self, parameters):
        """Resume from suspension with saved state."""
        # Restore state if provided
        if "saved_state" in parameters:
            try:
                # Restore state components
                saved_state = parameters["saved_state"]
                
                # Restore current directory
                if "current_directory" in saved_state:
                    self.state["current_directory"] = saved_state["current_directory"]
                
                # Restore bookmarks
                if "bookmarks" in saved_state:
                    self.state["bookmarks"] = saved_state["bookmarks"]
                
                # Restore recent items
                if "recent_items" in saved_state:
                    self.state["recent_items"] = saved_state["recent_items"]
                
                # Restore history
                if "history" in saved_state:
                    self.state["history"] = saved_state["history"]
                
                if "history_position" in saved_state:
                    self.state["history_position"] = saved_state["history_position"]
                
                logger.info("State restored successfully")
            except Exception as e:
                logger.error(f"Failed to restore state: {str(e)}")
        
        # Return success
        return {
            "status": "success",
            "state": "resumed"
        }
    
    async def release(self):
        """Prepare for release by cleaning up resources."""
        # Save bookmarks
        self._save_bookmarks()
        
        # Clear memory
        self.state["bookmarks"] = []
        self.state["recent_items"] = []
        
        return {
            "status": "success"
        }


# Create a FileManagerManifest to describe this cell
FileManagerManifest = {
    "name": "file_manager",
    "version": "1.0.0",
    "description": "A file manager cell for QCC",
    "author": "QCC Team",
    "license": "MIT",
    "capabilities": [
        {
            "name": "list_directory",
            "description": "List contents of a directory",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Directory path to list, defaults to current directory",
                    "required": False
                },
                {
                    "name": "show_hidden",
                    "type": "boolean",
                    "description": "Whether to show hidden files and directories",
                    "required": False
                },
                {
                    "name": "sort_by",
                    "type": "string",
                    "description": "Field to sort by (name, type, size, modified_at)",
                    "required": False
                },
                {
                    "name": "sort_order",
                    "type": "string",
                    "description": "Sort order (asc, desc)",
                    "required": False
                }
            ]
        },
        {
            "name": "create_directory",
            "description": "Create a new directory",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path where to create the directory",
                    "required": True
                },
                {
                    "name": "name",
                    "type": "string",
                    "description": "Name of the directory to create",
                    "required": True
                }
            ]
        },
        {
            "name": "create_file",
            "description": "Create a new file",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path where to create the file",
                    "required": True
                },
                {
                    "name": "name",
                    "type": "string",
                    "description": "Name of the file to create",
                    "required": True
                },
                {
                    "name": "content",
                    "type": "string",
                    "description": "Initial content of the file",
                    "required": False
                }
            ]
        },
        {
            "name": "delete_item",
            "description": "Delete a file or directory",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path to the item to delete",
                    "required": True
                },
                {
                    "name": "recursive",
                    "type": "boolean",
                    "description": "Whether to delete directories recursively",
                    "required": False
                }
            ]
        },
        {
            "name": "rename_item",
            "description": "Rename a file or directory",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path to the item to rename",
                    "required": True
                },
                {
                    "name": "new_name",
                    "type": "string",
                    "description": "New name for the item",
                    "required": True
                }
            ]
        },
        {
            "name": "copy_item",
            "description": "Copy a file or directory",
            "parameters": [
                {
                    "name": "source_path",
                    "type": "string",
                    "description": "Path to the item to copy",
                    "required": True
                },
                {
                    "name": "destination_path",
                    "type": "string",
                    "description": "Path where to copy the item",
                    "required": True
                },
                {
                    "name": "recursive",
                    "type": "boolean",
                    "description": "Whether to copy directories recursively",
                    "required": False
                }
            ]
        },
        {
            "name": "move_item",
            "description": "Move a file or directory",
            "parameters": [
                {
                    "name": "source_path",
                    "type": "string",
                    "description": "Path to the item to move",
                    "required": True
                },
                {
                    "name": "destination_path",
                    "type": "string",
                    "description": "Path where to move the item",
                    "required": True
                }
            ]
        },
        {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path to the file to read",
                    "required": True
                },
                {
                    "name": "encoding",
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "required": False
                },
                {
                    "name": "as_base64",
                    "type": "boolean",
                    "description": "Whether to return binary files as base64",
                    "required": False
                }
            ]
        },
        {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path to the file to write",
                    "required": True
                },
                {
                    "name": "content",
                    "type": "string",
                    "description": "Content to write",
                    "required": True
                },
                {
                    "name": "encoding",
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "required": False
                },
                {
                    "name": "is_base64",
                    "type": "boolean",
                    "description": "Whether the content is base64 encoded",
                    "required": False
                },
                {
                    "name": "mode",
                    "type": "string",
                    "description": "Write mode (write, append)",
                    "required": False
                }
            ]
        },
        {
            "name": "get_item_info",
            "description": "Get information about a file or directory",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Path to the item",
                    "required": True
                }
            ]
        },
        {
            "name": "search_items",
            "description": "Search for files and directories",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Root path to search in",
                    "required": True
                },
                {
                    "name": "query",
                    "type": "string",
                    "description": "Search query",
                    "required": True
                },
                {
                    "name": "recursive",
                    "type": "boolean",
                    "description": "Whether to search recursively",
                    "required": False
                },
                {
                    "name": "file_types",
                    "type": "array",
                    "description": "File types to include in search",
                    "required": False
                },
                {
                    "name": "include_hidden",
                    "type": "boolean",
                    "description": "Whether to include hidden files",
                    "required": False
                },
                {
                    "name": "max_results",
                    "type": "number",
                    "description": "Maximum number of results to return",
                    "required": False
                }
            ]
        },
        {
            "name": "get_file_explorer_ui",
            "description": "Get a file explorer UI",
            "parameters": [
                {
                    "name": "path",
                    "type": "string",
                    "description": "Initial path to display",
                    "required": False
                }
            ]
        }
    ],
    "dependencies": [],
    "resource_requirements": {
        "memory_mb": 30,
        "cpu_percent": 5,
        "storage_mb": 100
    }
}


# Example usage demonstration
async def example_usage():
    """Demonstrates how to use the FileManagerCell."""
    import asyncio
    
    # Create and initialize the cell
    file_manager = FileManagerCell()
    await file_manager.initialize({
        "cell_id": "demo-file-manager-cell",
        "quantum_signature": "demo-signature",
        "root_directory": "./example_files"
    })
    
    # Create a test directory
    create_dir_result = await file_manager.create_directory({
        "path": "./example_files",
        "name": "test_directory"
    })
    print(f"Created directory: {create_dir_result}")
    
    # Create a test file
    create_file_result = await file_manager.create_file({
        "path": "./example_files/test_directory",
        "name": "test_file.txt",
        "content": "This is a test file created by the FileManagerCell."
    })
    print(f"Created file: {create_file_result}")
    
    # List directory contents
    list_result = await file_manager.list_directory({
        "path": "./example_files/test_directory"
    })
    print(f"Directory contents: {list_result}")
    
    # Read file
    read_result = await file_manager.read_file({
        "path": "./example_files/test_directory/test_file.txt"
    })
    print(f"File content: {read_result}")
    
    # Get item info
    info_result = await file_manager.get_item_info({
        "path": "./example_files/test_directory/test_file.txt"
    })
    print(f"Item info: {info_result}")
    
    # Release the cell
    release_result = await file_manager.release()
    print(f"Released cell: {release_result}")


# Run the example if this script is executed directly
if __name__ == "__main__":
    import asyncio
    
    # Run the example
    asyncio.run(example_usage())

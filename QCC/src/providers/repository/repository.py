"""
Main repository implementation for the QCC Provider system.

This module provides the CellRepository class, which serves as the main interface
for storing, retrieving, and managing cells within the provider.
"""

import os
import logging
import yaml
import uuid
from typing import Dict, List, Any, Optional, Union, Set, Tuple

from .storage import StorageManager, StorageBackendType
from .indexing import IndexManager, IndexStrategy
from .versioning import VersionManager, VersionConflictError
from .metadata import MetadataManager, CellMetadata

logger = logging.getLogger(__name__)

class CellRepository:
    """
    Main repository class for cell storage, indexing, and querying.
    
    This class serves as the facade for the repository subsystem, coordinating 
    between storage, indexing, versioning, and metadata components.
    
    Attributes:
        storage_manager: Manages physical storage of cells
        index_manager: Provides indexing and search capabilities
        version_manager: Handles versioning of cells
        metadata_manager: Manages cell metadata
    """
    
    def __init__(
        self,
        storage_type: str = "local",
        storage_path: Optional[str] = None,
        index_strategy: str = "capability",
        enable_versioning: bool = True,
        config_file: Optional[str] = None
    ):
        """
        Initialize the cell repository.
        
        Args:
            storage_type: Type of storage backend ("local", "s3", "distributed")
            storage_path: Path for storage (if applicable)
            index_strategy: Indexing strategy to use
            enable_versioning: Whether to enable versioning
            config_file: Optional path to configuration file
        """
        # Load configuration if provided
        self.config = {}
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        
        # Initialize components
        storage_config = self.config.get('storage', {})
        storage_config.setdefault('type', storage_type)
        storage_config.setdefault('path', storage_path)
        
        self.storage_manager = StorageManager.create(storage_config)
        
        index_config = self.config.get('indexing', {})
        index_config.setdefault('strategy', index_strategy)
        
        self.index_manager = IndexManager(index_config)
        
        version_config = self.config.get('versioning', {})
        version_config.setdefault('enabled', enable_versioning)
        
        self.version_manager = VersionManager(version_config)
        
        metadata_config = self.config.get('metadata', {})
        self.metadata_manager = MetadataManager(metadata_config)
        
        logger.info(f"Cell repository initialized with storage type: {storage_type}, "
                   f"index strategy: {index_strategy}")
    
    def store_cell(self, cell_data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Store a cell in the repository.
        
        Args:
            cell_data: Binary data of the cell
            metadata: Cell metadata including capabilities, requirements, etc.
            
        Returns:
            cell_id: Unique identifier for the stored cell
            
        Raises:
            ValueError: If metadata is invalid
            StorageError: If storage fails
            VersionConflictError: If there's a version conflict
        """
        # Validate metadata
        cell_metadata = CellMetadata(metadata)
        self.metadata_manager.validate(cell_metadata)
        
        # Generate ID if not provided
        cell_id = metadata.get('id', str(uuid.uuid4()))
        version = metadata.get('version', '1.0.0')
        
        # Check for version conflicts
        if self.version_manager.exists(cell_id, version):
            if not self.version_manager.can_update(cell_id, version):
                raise VersionConflictError(f"Version {version} of cell {cell_id} already exists")
        
        # Store cell data
        storage_path = self.storage_manager.store(
            cell_id, 
            version, 
            cell_data, 
            cell_metadata.to_dict()
        )
        
        # Update index
        self.index_manager.index_cell(cell_id, version, cell_metadata)
        
        # Register version
        self.version_manager.register_version(cell_id, version, storage_path)
        
        logger.info(f"Stored cell {cell_id} version {version}")
        return cell_id
    
    def get_cell(self, cell_id: str, version: Optional[str] = None) -> Tuple[bytes, Dict[str, Any]]:
        """
        Retrieve a cell by ID and optionally version.
        
        Args:
            cell_id: ID of the cell to retrieve
            version: Specific version to retrieve (latest if None)
            
        Returns:
            Tuple of (cell_data, metadata)
            
        Raises:
            ValueError: If cell ID is invalid
            CellNotFoundError: If cell is not found
            VersionNotFoundError: If specified version is not found
        """
        # Resolve version if not specified
        if version is None:
            version = self.version_manager.get_latest_version(cell_id)
        
        # Get storage path
        storage_path = self.version_manager.get_storage_path(cell_id, version)
        
        # Retrieve cell data and metadata
        cell_data, metadata = self.storage_manager.retrieve(cell_id, version, storage_path)
        
        logger.debug(f"Retrieved cell {cell_id} version {version}")
        return cell_data, metadata
    
    def find_cells_by_capability(
        self,
        capabilities: List[str],
        version_constraint: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find cells matching the specified capabilities.
        
        Args:
            capabilities: List of required capabilities
            version_constraint: Version constraint (e.g., ">=1.2.0")
            limit: Maximum number of results
            offset: Offset for pagination
            additional_filters: Additional filters to apply
            
        Returns:
            List of cell metadata matching the query
        """
        # Find matching cells in index
        cell_versions = self.index_manager.find_by_capabilities(capabilities, additional_filters)
        
        # Apply version constraints
        if version_constraint:
            cell_versions = self.version_manager.filter_by_constraint(cell_versions, version_constraint)
        
        # Get full metadata for matching cells
        results = []
        for cell_id, version in cell_versions[offset:offset+limit]:
            _, metadata = self.get_cell(cell_id, version)
            results.append(metadata)
        
        return results
    
    def update_cell(self, cell_id: str, cell_data: bytes, metadata: Dict[str, Any]) -> str:
        """
        Update an existing cell.
        
        Args:
            cell_id: ID of the cell to update
            cell_data: New cell data
            metadata: New cell metadata
            
        Returns:
            Updated cell ID
            
        Raises:
            CellNotFoundError: If cell is not found
            VersionConflictError: If there's a version conflict
            ValueError: If metadata is invalid
        """
        # Ensure cell exists
        if not self.version_manager.has_cell(cell_id):
            raise ValueError(f"Cell {cell_id} not found")
        
        # Validate metadata
        cell_metadata = CellMetadata(metadata)
        self.metadata_manager.validate(cell_metadata)
        
        # Get version information
        version = metadata.get('version', '1.0.0')
        
        # Check for version conflicts
        if self.version_manager.exists(cell_id, version):
            if not self.version_manager.can_update(cell_id, version):
                raise VersionConflictError(f"Version {version} of cell {cell_id} already exists and cannot be updated")
        
        # Store updated cell
        storage_path = self.storage_manager.store(
            cell_id, 
            version, 
            cell_data, 
            cell_metadata.to_dict()
        )
        
        # Update index
        self.index_manager.update_index(cell_id, version, cell_metadata)
        
        # Update version registry
        self.version_manager.register_version(cell_id, version, storage_path)
        
        logger.info(f"Updated cell {cell_id} to version {version}")
        return cell_id
    
    def remove_cell(self, cell_id: str, version: Optional[str] = None) -> bool:
        """
        Remove a cell from the repository.
        
        Args:
            cell_id: ID of the cell to remove
            version: Specific version to remove (all versions if None)
            
        Returns:
            True if successful, False otherwise
        """
        # Get versions to remove
        versions_to_remove = []
        if version:
            versions_to_remove = [(cell_id, version)]
        else:
            versions_to_remove = self.version_manager.get_all_versions(cell_id)
        
        # Remove each version
        for _, ver in versions_to_remove:
            # Get storage path before removing from version manager
            storage_path = self.version_manager.get_storage_path(cell_id, ver)
            
            # Remove from storage
            self.storage_manager.remove(cell_id, ver, storage_path)
            
            # Remove from index
            self.index_manager.remove_from_index(cell_id, ver)
            
            # Remove from version registry
            self.version_manager.remove_version(cell_id, ver)
            
            logger.info(f"Removed cell {cell_id} version {ver}")
        
        return True
    
    def get_cell_versions(self, cell_id: str) -> List[str]:
        """
        Get all versions of a cell.
        
        Args:
            cell_id: ID of the cell
            
        Returns:
            List of version strings
        """
        return self.version_manager.get_version_list(cell_id)
    
    def list_cells(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List cells in the repository.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of cell metadata
        """
        # Get cell IDs from index
        cell_versions = self.index_manager.list_all(limit, offset)
        
        # Get full metadata for each cell
        results = []
        for cell_id, version in cell_versions:
            _, metadata = self.get_cell(cell_id, version)
            results.append(metadata)
        
        return results
    
    def search_cells(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching cell metadata
        """
        # Search in index
        cell_versions = self.index_manager.search(query, limit)
        
        # Get full metadata for each result
        results = []
        for cell_id, version in cell_versions:
            _, metadata = self.get_cell(cell_id, version)
            results.append(metadata)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get repository statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            "total_cells": self.index_manager.count_cells(),
            "total_versions": self.version_manager.count_versions(),
            "storage_usage": self.storage_manager.get_usage(),
            "capability_counts": self.index_manager.get_capability_counts(),
            "top_cells": self.metadata_manager.get_top_cells(10)
        }
        return stats

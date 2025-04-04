"""
Indexing system for cell repositories.

This module provides classes for indexing cells based on their capabilities
and other metadata, enabling efficient search and retrieval.
"""

import logging
import json
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Set, Union

from .metadata import CellMetadata

logger = logging.getLogger(__name__)

class IndexStrategy(Enum):
    """Enumeration of indexing strategies."""
    SIMPLE = "simple"
    CAPABILITY = "capability"
    VECTOR = "vector"
    HYBRID = "hybrid"

class IndexError(Exception):
    """Exception raised for indexing-related errors."""
    pass

class IndexManager:
    """
    Manager for cell indexes.
    
    This class provides a facade for different indexing strategies and
    manages the creation, updating, and querying of indexes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize index manager.
        
        Args:
            config: Indexing configuration
        """
        self.config = config
        strategy = config.get('strategy', 'capability')
        
        # Create appropriate index based on strategy
        if strategy == IndexStrategy.SIMPLE.value:
            self.index = SimpleIndex(config)
        elif strategy == IndexStrategy.CAPABILITY.value:
            self.index = CapabilityIndex(config)
        elif strategy == IndexStrategy.VECTOR.value:
            self.index = VectorIndex(config)
        elif strategy == IndexStrategy.HYBRID.value:
            self.index = HybridIndex(config)
        else:
            raise ValueError(f"Unsupported index strategy: {strategy}")
        
        logger.info(f"Initialized index manager with strategy: {strategy}")
    
    def index_cell(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Index a cell.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        self.index.add(cell_id, version, metadata)
    
    def update_index(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Update index entry for a cell.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Updated cell metadata
        """
        self.index.update(cell_id, version, metadata)
    
    def remove_from_index(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        self.index.remove(cell_id, version)
    
    def find_by_capabilities(
        self, 
        capabilities: List[str],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Find cells with specific capabilities.
        
        Args:
            capabilities: List of required capabilities
            additional_filters: Additional filters to apply
            
        Returns:
            List of (cell_id, version) tuples
        """
        return self.index.find_by_capabilities(capabilities, additional_filters)
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        return self.index.search(query, limit)
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Tuple[str, str]]:
        """
        List all cells in the index.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of (cell_id, version) tuples
        """
        return self.index.list_all(limit, offset)
    
    def count_cells(self) -> int:
        """
        Count total number of cells in the index.
        
        Returns:
            Cell count
        """
        return self.index.count_cells()
    
    def get_capability_counts(self) -> Dict[str, int]:
        """
        Get counts of cells by capability.
        
        Returns:
            Dictionary mapping capability names to counts
        """
        return self.index.get_capability_counts()

class BaseIndex:
    """Base class for index implementations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize index.
        
        Args:
            config: Index configuration
        """
        self.config = config
    
    def add(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Add a cell to the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        raise NotImplementedError("Subclasses must implement add method")
    
    def update(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Update a cell in the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Updated cell metadata
        """
        raise NotImplementedError("Subclasses must implement update method")
    
    def remove(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        raise NotImplementedError("Subclasses must implement remove method")
    
    def find_by_capabilities(
        self, 
        capabilities: List[str],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Find cells with specific capabilities.
        
        Args:
            capabilities: List of required capabilities
            additional_filters: Additional filters to apply
            
        Returns:
            List of (cell_id, version) tuples
        """
        raise NotImplementedError("Subclasses must implement find_by_capabilities method")
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        raise NotImplementedError("Subclasses must implement search method")
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Tuple[str, str]]:
        """
        List all cells in the index.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of (cell_id, version) tuples
        """
        raise NotImplementedError("Subclasses must implement list_all method")
    
    def count_cells(self) -> int:
        """
        Count total number of cells in the index.
        
        Returns:
            Cell count
        """
        raise NotImplementedError("Subclasses must implement count_cells method")
    
    def get_capability_counts(self) -> Dict[str, int]:
        """
        Get counts of cells by capability.
        
        Returns:
            Dictionary mapping capability names to counts
        """
        raise NotImplementedError("Subclasses must implement get_capability_counts method")

class SimpleIndex(BaseIndex):
    """
    Simple in-memory index implementation.
    
    This index maintains a dictionary of all cells keyed by ID and version.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize simple index.
        
        Args:
            config: Index configuration
        """
        super().__init__(config)
        
        # Dictionary of cells by ID and version
        self.cells: Dict[str, Dict[str, CellMetadata]] = {}
        
        # Dictionary mapping cell IDs to latest version
        self.latest_versions: Dict[str, str] = {}
        
        logger.info("Initialized simple index")
    
    def add(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Add a cell to the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        # Initialize cell dict if needed
        if cell_id not in self.cells:
            self.cells[cell_id] = {}
        
        # Add cell metadata
        self.cells[cell_id][version] = metadata
        
        # Update latest version if needed
        if cell_id not in self.latest_versions or version > self.latest_versions[cell_id]:
            self.latest_versions[cell_id] = version
        
        logger.debug(f"Added cell {cell_id} version {version} to simple index")
    
    def update(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Update a cell in the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Updated cell metadata
            
        Raises:
            IndexError: If cell not found
        """
        if cell_id not in self.cells or version not in self.cells[cell_id]:
            raise IndexError(f"Cell {cell_id} version {version} not found in index")
        
        # Update cell metadata
        self.cells[cell_id][version] = metadata
        
        logger.debug(f"Updated cell {cell_id} version {version} in simple index")
    
    def remove(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        if cell_id in self.cells and version in self.cells[cell_id]:
            # Remove version
            del self.cells[cell_id][version]
            
            # If no versions left, remove cell ID
            if not self.cells[cell_id]:
                del self.cells[cell_id]
                if cell_id in self.latest_versions:
                    del self.latest_versions[cell_id]
            else:
                # Update latest version if needed
                if cell_id in self.latest_versions and version == self.latest_versions[cell_id]:
                    self.latest_versions[cell_id] = max(self.cells[cell_id].keys())
            
            logger.debug(f"Removed cell {cell_id} version {version} from simple index")
    
    def find_by_capabilities(
        self, 
        capabilities: List[str],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Find cells with specific capabilities.
        
        Args:
            capabilities: List of required capabilities
            additional_filters: Additional filters to apply
            
        Returns:
            List of (cell_id, version) tuples
        """
        matching_cells = []
        
        # Check all cells in the index
        for cell_id, versions in self.cells.items():
            for version, metadata in versions.items():
                # Check if all required capabilities are present
                cell_capabilities = metadata.get("capabilities", [])
                
                if all(cap in cell_capabilities for cap in capabilities):
                    # Apply additional filters if provided
                    if additional_filters:
                        match = True
                        for key, value in additional_filters.items():
                            if key not in metadata or metadata[key] != value:
                                match = False
                                break
                        
                        if not match:
                            continue
                    
                    matching_cells.append((cell_id, version))
        
        return matching_cells
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        query = query.lower()
        matching_cells = []
        
        # Simple text search in metadata
        for cell_id, versions in self.cells.items():
            for version, metadata in versions.items():
                # Check cell ID
                if query in cell_id.lower():
                    matching_cells.append((cell_id, version))
                    continue
                
                # Check metadata fields
                for key, value in metadata.items():
                    if isinstance(value, str) and query in value.lower():
                        matching_cells.append((cell_id, version))
                        break
                    
                    # Check lists of strings
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        if any(query in item.lower() for item in value):
                            matching_cells.append((cell_id, version))
                            break
                
                # Limit results
                if len(matching_cells) >= limit:
                    break
            
            # Limit results
            if len(matching_cells) >= limit:
                break
        
        return matching_cells[:limit]
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Tuple[str, str]]:
        """
        List all cells in the index.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of (cell_id, version) tuples
        """
        all_cells = []
        
        for cell_id, versions in self.cells.items():
            for version in versions.keys():
                all_cells.append((cell_id, version))
        
        # Sort by cell ID and version
        all_cells.sort()
        
        # Apply pagination
        return all_cells[offset:offset+limit]
    
    def count_cells(self) -> int:
        """
        Count total number of cells in the index.
        
        Returns:
            Cell count
        """
        return len(self.cells)
    
    def get_capability_counts(self) -> Dict[str, int]:
        """
        Get counts of cells by capability.
        
        Returns:
            Dictionary mapping capability names to counts
        """
        counts = {}
        
        # Count occurrences of each capability
        for cell_id, versions in self.cells.items():
            # Only count latest version
            latest_version = self.latest_versions.get(cell_id)
            if latest_version and latest_version in versions:
                metadata = versions[latest_version]
                capabilities = metadata.get("capabilities", [])
                
                for capability in capabilities:
                    counts[capability] = counts.get(capability, 0) + 1
        
        return counts

class CapabilityIndex(BaseIndex):
    """
    Capability-based index implementation.
    
    This index maintains mappings from capabilities to cells,
    enabling efficient lookup by capability.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize capability index.
        
        Args:
            config: Index configuration
        """
        super().__init__(config)
        
        # Dictionary of cells by ID and version
        self.cells: Dict[str, Dict[str, CellMetadata]] = {}
        
        # Dictionary mapping cell IDs to latest version
        self.latest_versions: Dict[str, str] = {}
        
        # Dictionary mapping capabilities to (cell_id, version) tuples
        self.capability_map: Dict[str, List[Tuple[str, str]]] = {}
        
        # Cache for full-text search
        self.text_index: Dict[str, Set[Tuple[str, str]]] = {}
        
        # Cache update settings
        self.update_text_index = config.get('update_text_index', True)
        
        logger.info("Initialized capability index")
    
    def add(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Add a cell to the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        # Initialize cell dict if needed
        if cell_id not in self.cells:
            self.cells[cell_id] = {}
        
        # Add cell metadata
        self.cells[cell_id][version] = metadata
        
        # Update latest version if needed
        if cell_id not in self.latest_versions or version > self.latest_versions[cell_id]:
            self.latest_versions[cell_id] = version
        
        # Update capability map
        capabilities = metadata.get("capabilities", [])
        for capability in capabilities:
            if capability not in self.capability_map:
                self.capability_map[capability] = []
            
            if (cell_id, version) not in self.capability_map[capability]:
                self.capability_map[capability].append((cell_id, version))
        
        # Update text index if enabled
        if self.update_text_index:
            self._index_text(cell_id, version, metadata)
        
        logger.debug(f"Added cell {cell_id} version {version} to capability index")
    
    def update(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Update a cell in the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Updated cell metadata
            
        Raises:
            IndexError: If cell not found
        """
        if cell_id not in self.cells or version not in self.cells[cell_id]:
            raise IndexError(f"Cell {cell_id} version {version} not found in index")
        
        # Get old metadata for updating indexes
        old_metadata = self.cells[cell_id][version]
        old_capabilities = old_metadata.get("capabilities", [])
        
        # Update cell metadata
        self.cells[cell_id][version] = metadata
        
        # Update capability map
        new_capabilities = metadata.get("capabilities", [])
        
        # Remove from old capabilities that are no longer present
        for capability in old_capabilities:
            if capability not in new_capabilities:
                if capability in self.capability_map:
                    if (cell_id, version) in self.capability_map[capability]:
                        self.capability_map[capability].remove((cell_id, version))
                    
                    # Remove empty capability entries
                    if not self.capability_map[capability]:
                        del self.capability_map[capability]
        
        # Add to new capabilities
        for capability in new_capabilities:
            if capability not in old_capabilities:
                if capability not in self.capability_map:
                    self.capability_map[capability] = []
                
                if (cell_id, version) not in self.capability_map[capability]:
                    self.capability_map[capability].append((cell_id, version))
        
        # Update text index if enabled
        if self.update_text_index:
            self._remove_from_text_index(cell_id, version)
            self._index_text(cell_id, version, metadata)
        
        logger.debug(f"Updated cell {cell_id} version {version} in capability index")
    
    def remove(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        if cell_id in self.cells and version in self.cells[cell_id]:
            # Get metadata before removing
            metadata = self.cells[cell_id][version]
            capabilities = metadata.get("capabilities", [])
            
            # Remove from capability map
            for capability in capabilities:
                if capability in self.capability_map:
                    if (cell_id, version) in self.capability_map[capability]:
                        self.capability_map[capability].remove((cell_id, version))
                    
                    # Remove empty capability entries
                    if not self.capability_map[capability]:
                        del self.capability_map[capability]
            
            # Remove from text index
            if self.update_text_index:
                self._remove_from_text_index(cell_id, version)
            
            # Remove version
            del self.cells[cell_id][version]
            
            # If no versions left, remove cell ID
            if not self.cells[cell_id]:
                del self.cells[cell_id]
                if cell_id in self.latest_versions:
                    del self.latest_versions[cell_id]
            else:
                # Update latest version if needed
                if cell_id in self.latest_versions and version == self.latest_versions[cell_id]:
                    self.latest_versions[cell_id] = max(self.cells[cell_id].keys())
            
            logger.debug(f"Removed cell {cell_id} version {version} from capability index")
    
    def find_by_capabilities(
        self, 
        capabilities: List[str],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Find cells with specific capabilities.
        
        Args:
            capabilities: List of required capabilities
            additional_filters: Additional filters to apply
            
        Returns:
            List of (cell_id, version) tuples
        """
        if not capabilities:
            return []
        
        # Start with cells matching the first capability
        matching_cells = set(self.capability_map.get(capabilities[0], []))
        
        # Intersect with cells matching other capabilities
        for capability in capabilities[1:]:
            capability_cells = set(self.capability_map.get(capability, []))
            matching_cells = matching_cells.intersection(capability_cells)
        
        # Apply additional filters if provided
        if additional_filters:
            filtered_cells = []
            for cell_id, version in matching_cells:
                metadata = self.cells[cell_id][version]
                match = True
                
                for key, value in additional_filters.items():
                    if key not in metadata or metadata[key] != value:
                        match = False
                        break
                
                if match:
                    filtered_cells.append((cell_id, version))
            
            return filtered_cells
        
        return list(matching_cells)
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        if not self.update_text_index:
            # Fall back to simple search if text index is disabled
            return self._simple_search(query, limit)
        
        query = query.lower()
        
        # Split query into tokens
        tokens = query.split()
        
        if not tokens:
            return []
        
        # Find cells matching all tokens
        matching_cells = set()
        first_token = True
        
        for token in tokens:
            token_cells = set()
            
            # Look for token in text index
            for indexed_token, cells in self.text_index.items():
                if token in indexed_token:
                    token_cells.update(cells)
            
            # If first token, initialize matching_cells
            if first_token:
                matching_cells = token_cells
                first_token = False
            else:
                # Intersect with cells matching other tokens
                matching_cells = matching_cells.intersection(token_cells)
        
        return list(matching_cells)[:limit]
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Tuple[str, str]]:
        """
        List all cells in the index.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of (cell_id, version) tuples
        """
        all_cells = []
        
        for cell_id, versions in self.cells.items():
            for version in versions.keys():
                all_cells.append((cell_id, version))
        
        # Sort by cell ID and version
        all_cells.sort()
        
        # Apply pagination
        return all_cells[offset:offset+limit]
    
    def count_cells(self) -> int:
        """
        Count total number of cells in the index.
        
        Returns:
            Cell count
        """
        return len(self.cells)
    
    def get_capability_counts(self) -> Dict[str, int]:
        """
        Get counts of cells by capability.
        
        Returns:
            Dictionary mapping capability names to counts
        """
        counts = {}
        
        # Count cells for each capability
        for capability, cells in self.capability_map.items():
            counts[capability] = len(cells)
        
        return counts
    
    def _index_text(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Index text content of metadata for search.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        # Extract textual content for indexing
        text_fields = []
        
        # Add cell ID
        text_fields.append(cell_id)
        
        # Add metadata fields
        for key, value in metadata.items():
            if isinstance(value, str):
                text_fields.append(value)
            elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                text_fields.extend(value)
            elif isinstance(value, dict):
                # Add string values from dictionary
                for k, v in value.items():
                    if isinstance(v, str):
                        text_fields.append(v)
        
        # Tokenize and index
        for field in text_fields:
            # Convert to lowercase and split into words
            words = field.lower().split()
            
            for word in words:
                if len(word) < 3:
                    continue  # Skip very short words
                
                if word not in self.text_index:
                    self.text_index[word] = set()
                
                self.text_index[word].add((cell_id, version))
    
    def _remove_from_text_index(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the text index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        for word, cells in list(self.text_index.items()):
            if (cell_id, version) in cells:
                cells.remove((cell_id, version))
                
                # Remove empty entries
                if not cells:
                    del self.text_index[word]
    
    def _simple_search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Perform a simple search when text index is disabled.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        query = query.lower()
        matching_cells = []
        
        # Simple text search in metadata
        for cell_id, versions in self.cells.items():
            for version, metadata in versions.items():
                # Check cell ID
                if query in cell_id.lower():
                    matching_cells.append((cell_id, version))
                    continue
                
                # Check metadata fields
                for key, value in metadata.items():
                    if isinstance(value, str) and query in value.lower():
                        matching_cells.append((cell_id, version))
                        break
                    
                    # Check lists of strings
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        if any(query in item.lower() for item in value):
                            matching_cells.append((cell_id, version))
                            break
                
                # Limit results
                if len(matching_cells) >= limit:
                    break
            
            # Limit results
            if len(matching_cells) >= limit:
                break
        
        return matching_cells[:limit]

class VectorIndex(BaseIndex):
    """
    Vector-based index implementation.
    
    This is a placeholder implementation. In a real implementation,
    this would use vector embeddings for semantic search.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vector index.
        
        Args:
            config: Index configuration
        """
        super().__init__(config)
        
        # Dictionary of cells by ID and version
        self.cells: Dict[str, Dict[str, CellMetadata]] = {}
        
        # Placeholder for vector embeddings
        self.embeddings: Dict[Tuple[str, str], List[float]] = {}
        
        logger.info("Initialized vector index")
    
    def add(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Add a cell to the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        # Initialize cell dict if needed
        if cell_id not in self.cells:
            self.cells[cell_id] = {}
        
        # Add cell metadata
        self.cells[cell_id][version] = metadata
        
        # In a real implementation, compute vector embedding here
        logger.debug(f"Added cell {cell_id} version {version} to vector index")
    
    def update(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Update a cell in the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Updated cell metadata
            
        Raises:
            IndexError: If cell not found
        """
        if cell_id not in self.cells or version not in self.cells[cell_id]:
            raise IndexError(f"Cell {cell_id} version {version} not found in index")
        
        # Update cell metadata
        self.cells[cell_id][version] = metadata
        
        # In a real implementation, update vector embedding here
        logger.debug(f"Updated cell {cell_id} version {version} in vector index")
    
    def remove(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        if cell_id in self.cells and version in self.cells[cell_id]:
            # Remove from cells dict
            del self.cells[cell_id][version]
            
            # If no versions left, remove cell ID
            if not self.cells[cell_id]:
                del self.cells[cell_id]
            
            # Remove embedding if present
            if (cell_id, version) in self.embeddings:
                del self.embeddings[(cell_id, version)]
            
            logger.debug(f"Removed cell {cell_id} version {version} from vector index")
    
    def find_by_capabilities(
        self, 
        capabilities: List[str],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Find cells with specific capabilities.
        
        Args:
            capabilities: List of required capabilities
            additional_filters: Additional filters to apply
            
        Returns:
            List of (cell_id, version) tuples
        """
        matching_cells = []
        
        # Check all cells in the index
        for cell_id, versions in self.cells.items():
            for version, metadata in versions.items():
                # Check if all required capabilities are present
                cell_capabilities = metadata.get("capabilities", [])
                
                if all(cap in cell_capabilities for cap in capabilities):
                    # Apply additional filters if provided
                    if additional_filters:
                        match = True
                        for key, value in additional_filters.items():
                            if key not in metadata or metadata[key] != value:
                                match = False
                                break
                        
                        if not match:
                            continue
                    
                    matching_cells.append((cell_id, version))
        
        return matching_cells
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        # In a real implementation, this would:
        # 1. Convert query to vector embedding
        # 2. Find nearest neighbors in vector space
        
        # Placeholder implementation
        query = query.lower()
        matching_cells = []
        
        # Simple text search in metadata
        for cell_id, versions in self.cells.items():
            for version, metadata in versions.items():
                # Check cell ID
                if query in cell_id.lower():
                    matching_cells.append((cell_id, version))
                    continue
                
                # Check metadata fields
                for key, value in metadata.items():
                    if isinstance(value, str) and query in value.lower():
                        matching_cells.append((cell_id, version))
                        break
                    
                    # Check lists of strings
                    if isinstance(value, list) and all(isinstance(item, str) for item in value):
                        if any(query in item.lower() for item in value):
                            matching_cells.append((cell_id, version))
                            break
                
                # Limit results
                if len(matching_cells) >= limit:
                    break
            
            # Limit results
            if len(matching_cells) >= limit:
                break
        
        return matching_cells[:limit]
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Tuple[str, str]]:
        """
        List all cells in the index.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of (cell_id, version) tuples
        """
        all_cells = []
        
        for cell_id, versions in self.cells.items():
            for version in versions.keys():
                all_cells.append((cell_id, version))
        
        # Sort by cell ID and version
        all_cells.sort()
        
        # Apply pagination
        return all_cells[offset:offset+limit]
    
    def count_cells(self) -> int:
        """
        Count total number of cells in the index.
        
        Returns:
            Cell count
        """
        return len(self.cells)
    
    def get_capability_counts(self) -> Dict[str, int]:
        """
        Get counts of cells by capability.
        
        Returns:
            Dictionary mapping capability names to counts
        """
        counts = {}
        
        # Count occurrences of each capability
        for cell_id, versions in self.cells.items():
            for version, metadata in versions.items():
                capabilities = metadata.get("capabilities", [])
                
                for capability in capabilities:
                    counts[capability] = counts.get(capability, 0) + 1
        
        return counts

class HybridIndex(BaseIndex):
    """
    Hybrid index implementation that combines multiple indexing strategies.
    
    This index uses both capability-based and vector-based indexing
    for different query types.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize hybrid index.
        
        Args:
            config: Index configuration
        """
        super().__init__(config)
        
        # Create component indexes
        capability_config = config.copy()
        capability_config['strategy'] = 'capability'
        self.capability_index = CapabilityIndex(capability_config)
        
        vector_config = config.copy()
        vector_config['strategy'] = 'vector'
        self.vector_index = VectorIndex(vector_config)
        
        logger.info("Initialized hybrid index")
    
    def add(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Add a cell to the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Cell metadata
        """
        # Add to both indexes
        self.capability_index.add(cell_id, version, metadata)
        self.vector_index.add(cell_id, version, metadata)
        
        logger.debug(f"Added cell {cell_id} version {version} to hybrid index")
    
    def update(self, cell_id: str, version: str, metadata: CellMetadata) -> None:
        """
        Update a cell in the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
            metadata: Updated cell metadata
            
        Raises:
            IndexError: If cell not found
        """
        # Update in both indexes
        self.capability_index.update(cell_id, version, metadata)
        self.vector_index.update(cell_id, version, metadata)
        
        logger.debug(f"Updated cell {cell_id} version {version} in hybrid index")
    
    def remove(self, cell_id: str, version: str) -> None:
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Cell identifier
            version: Cell version
        """
        # Remove from both indexes
        self.capability_index.remove(cell_id, version)
        self.vector_index.remove(cell_id, version)
        
        logger.debug(f"Removed cell {cell_id} version {version} from hybrid index")
    
    def find_by_capabilities(
        self, 
        capabilities: List[str],
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Find cells with specific capabilities.
        
        Args:
            capabilities: List of required capabilities
            additional_filters: Additional filters to apply
            
        Returns:
            List of (cell_id, version) tuples
        """
        # Use capability index for this query type
        return self.capability_index.find_by_capabilities(capabilities, additional_filters)
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Search for cells using a text query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (cell_id, version) tuples
        """
        # Use vector index for this query type
        vector_results = self.vector_index.search(query, limit)
        
        # Combine with capability index results for better coverage
        capability_results = self.capability_index.search(query, limit)
        
        # Merge results, prioritizing vector results
        combined_results = vector_results.copy()
        
        for result in capability_results:
            if result not in combined_results:
                combined_results.append(result)
                if len(combined_results) >= limit:
                    break
        
        return combined_results[:limit]
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Tuple[str, str]]:
        """
        List all cells in the index.
        
        Args:
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of (cell_id, version) tuples
        """
        # Use capability index for this query type
        return self.capability_index.list_all(limit, offset)
    
    def count_cells(self) -> int:
        """
        Count total number of cells in the index.
        
        Returns:
            Cell count
        """
        # Use capability index for this query type
        return self.capability_index.count_cells()
    
    def get_capability_counts(self) -> Dict[str, int]:
        """
        Get counts of cells by capability.
        
        Returns:
            Dictionary mapping capability names to counts
        """
        # Use capability index for this query type
        return self.capability_index.get_capability_counts()

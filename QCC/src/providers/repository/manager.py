"""
Repository Manager for QCC Cell Providers.

This module implements the core functionality for managing repositories of cells,
including storage, retrieval, indexing, and querying capabilities.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import json
import os
import shutil
import aiofiles
from aiofiles import os as aio_os
import hashlib
import re

from qcc.common.exceptions import RepositoryError, CellNotFoundError

logger = logging.getLogger(__name__)

class RepositoryManager:
    """
    Manages the repository of cells for a provider.
    
    The RepositoryManager is responsible for storing, retrieving, and indexing
    cells, as well as tracking capabilities and versions.
    
    Attributes:
        repo_id (str): Unique identifier for this repository
        storage_path (str): Directory path for cell storage
        index (Dict): Index of available cells by various criteria
        capabilities (Dict): Map of capabilities to cell types
        cell_types (Dict): Map of cell types to cell metadata
        config (Dict): Repository configuration
    """
    
    def __init__(self, storage_path: str = None, config: Dict[str, Any] = None):
        """
        Initialize the Repository Manager.
        
        Args:
            storage_path: Directory path for cell storage
            config: Repository configuration
        """
        self.repo_id = str(uuid.uuid4())
        self.storage_path = storage_path or "./data/cells"
        self.config = config or {}
        
        # Initialize indexes and maps
        self.index = {
            "by_id": {},
            "by_type": {},
            "by_capability": {},
            "by_version": {}
        }
        
        self.capabilities = {}
        self.cell_types = {}
        
        # Performance metrics
        self.start_time = datetime.now()
        self.total_retrievals = 0
        self.total_registrations = 0
        self.cache_hits = 0
        
        # Initialize in-memory cache
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_max_size = self.config.get("cache_max_size", 100)
        self.cell_cache = {}
        self.cache_access_times = {}
        
        logger.info(f"Repository Manager initialized with ID {self.repo_id}")
    
    async def initialize(self):
        """
        Initialize the repository.
        
        This method sets up the storage directory and loads the index.
        """
        logger.info(f"Initializing repository at {self.storage_path}")
        
        # Ensure storage directory exists
        await self._ensure_storage_path()
        
        # Load index
        await self._load_index()
        
        # Start background tasks
        if self.config.get("auto_index_rebuild_enabled", True):
            self._index_rebuild_task = asyncio.create_task(self._periodic_index_rebuild())
        
        logger.info(f"Repository initialization complete. Found {len(self.index['by_id'])} cells")
    
    async def _ensure_storage_path(self):
        """Ensure the storage directory exists."""
        try:
            if not os.path.exists(self.storage_path):
                os.makedirs(self.storage_path, exist_ok=True)
                logger.info(f"Created storage directory: {self.storage_path}")
                
            # Create subdirectories if they don't exist
            subdirs = ["metadata", "packages", "index"]
            for subdir in subdirs:
                subdir_path = os.path.join(self.storage_path, subdir)
                if not os.path.exists(subdir_path):
                    os.makedirs(subdir_path, exist_ok=True)
                    logger.info(f"Created subdirectory: {subdir_path}")
        
        except Exception as e:
            logger.error(f"Failed to create storage directories: {e}")
            raise RepositoryError(f"Failed to initialize repository storage: {e}")
    
    async def _load_index(self):
        """Load the repository index from storage."""
        index_path = os.path.join(self.storage_path, "index", "repository_index.json")
        
        try:
            if os.path.exists(index_path):
                async with aiofiles.open(index_path, 'r') as f:
                    index_data = json.loads(await f.read())
                    
                self.index = index_data.get("index", {
                    "by_id": {},
                    "by_type": {},
                    "by_capability": {},
                    "by_version": {}
                })
                
                self.capabilities = index_data.get("capabilities", {})
                self.cell_types = index_data.get("cell_types", {})
                
                logger.info(f"Loaded index with {len(self.index['by_id'])} cells")
            else:
                # If no index exists, rebuild it
                await self._rebuild_index()
                
        except Exception as e:
            logger.error(f"Failed to load index: {e}", exc_info=True)
            logger.info("Rebuilding index due to load failure")
            await self._rebuild_index()
    
    async def _save_index(self):
        """Save the repository index to storage."""
        index_path = os.path.join(self.storage_path, "index", "repository_index.json")
        
        try:
            # Prepare index data
            index_data = {
                "index": self.index,
                "capabilities": self.capabilities,
                "cell_types": self.cell_types,
                "updated_at": datetime.now().isoformat()
            }
            
            # Create backup of existing index if it exists
            if os.path.exists(index_path) and self.config.get("backup_index", True):
                backup_path = f"{index_path}.{int(time.time())}.bak"
                shutil.copy2(index_path, backup_path)
                
                # Clean up old backups
                if self.config.get("max_index_backups", 5) > 0:
                    backup_pattern = re.compile(r"repository_index\.json\.(\d+)\.bak$")
                    backups = []
                    
                    for filename in os.listdir(os.path.dirname(index_path)):
                        match = backup_pattern.match(filename)
                        if match:
                            backups.append(os.path.join(os.path.dirname(index_path), filename))
                    
                    # Sort backups by timestamp (most recent first)
                    backups.sort(reverse=True)
                    
                    # Remove excess backups
                    for old_backup in backups[self.config.get("max_index_backups", 5):]:
                        os.remove(old_backup)
            
            # Write index data to temporary file first
            temp_path = f"{index_path}.tmp"
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write(json.dumps(index_data, indent=2))
            
            # Rename temporary file to actual index file (atomic operation)
            os.replace(temp_path, index_path)
            
            logger.debug(f"Index saved with {len(self.index['by_id'])} cells")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}", exc_info=True)
            raise RepositoryError(f"Failed to save repository index: {e}")
    
    async def _rebuild_index(self):
        """Rebuild the entire repository index by scanning storage."""
        logger.info("Rebuilding repository index")
        
        # Reset indexes
        self.index = {
            "by_id": {},
            "by_type": {},
            "by_capability": {},
            "by_version": {}
        }
        
        self.capabilities = {}
        self.cell_types = {}
        
        try:
            # Scan metadata directory
            metadata_dir = os.path.join(self.storage_path, "metadata")
            if os.path.exists(metadata_dir):
                metadata_files = [f for f in os.listdir(metadata_dir) if f.endswith(".json")]
                
                for filename in metadata_files:
                    try:
                        # Extract cell ID from filename
                        cell_id = filename.replace(".json", "")
                        
                        # Load metadata
                        metadata_path = os.path.join(metadata_dir, filename)
                        async with aiofiles.open(metadata_path, 'r') as f:
                            metadata = json.loads(await f.read())
                        
                        # Check if package exists
                        package_path = os.path.join(self.storage_path, "packages", f"{cell_id}.package")
                        package_exists = os.path.exists(package_path)
                        
                        if not package_exists and not self.config.get("index_metadata_only", False):
                            logger.warning(f"Package missing for cell {cell_id}, skipping")
                            continue
                        
                        # Index the cell
                        self._add_to_index(cell_id, metadata)
                        
                    except Exception as e:
                        logger.error(f"Error indexing cell {filename}: {e}")
            
            # Save the rebuilt index
            await self._save_index()
            
            logger.info(f"Index rebuilt with {len(self.index['by_id'])} cells")
            
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}", exc_info=True)
            raise RepositoryError(f"Failed to rebuild repository index: {e}")
    
    async def _periodic_index_rebuild(self):
        """Periodically rebuild the index to ensure consistency."""
        rebuild_interval = self.config.get("index_rebuild_interval_hours", 24)
        
        while True:
            try:
                # Sleep for the configured interval
                await asyncio.sleep(rebuild_interval * 3600)
                
                # Rebuild index
                logger.info(f"Performing scheduled index rebuild")
                await self._rebuild_index()
                
            except asyncio.CancelledError:
                logger.info("Index rebuild task cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in periodic index rebuild: {e}", exc_info=True)
                # Sleep for a shorter interval on error
                await asyncio.sleep(3600)
    
    def _add_to_index(self, cell_id: str, metadata: Dict[str, Any]):
        """
        Add a cell to the index.
        
        Args:
            cell_id: Unique identifier for the cell
            metadata: Cell metadata
        """
        # Extract key information
        cell_type = metadata.get("cell_type")
        capability = metadata.get("capability")
        version = metadata.get("version", "latest")
        
        if not cell_type or not capability:
            logger.warning(f"Cell {cell_id} missing required metadata (type or capability)")
            return
        
        # Add to ID index
        self.index["by_id"][cell_id] = {
            "cell_type": cell_type,
            "capability": capability,
            "version": version,
            "indexed_at": datetime.now().isoformat()
        }
        
        # Add to type index
        if cell_type not in self.index["by_type"]:
            self.index["by_type"][cell_type] = {}
        
        if version not in self.index["by_type"][cell_type]:
            self.index["by_type"][cell_type][version] = cell_id
        
        # Add to capability index
        if capability not in self.index["by_capability"]:
            self.index["by_capability"][capability] = []
        
        if cell_id not in self.index["by_capability"][capability]:
            self.index["by_capability"][capability].append(cell_id)
        
        # Add to version index
        version_key = f"{cell_type}:{version}"
        self.index["by_version"][version_key] = cell_id
        
        # Update capabilities map
        if capability not in self.capabilities:
            self.capabilities[capability] = []
        
        if cell_type not in self.capabilities[capability]:
            self.capabilities[capability].append(cell_type)
        
        # Update cell types map
        self.cell_types[cell_type] = {
            "latest_version": version,
            "capabilities": [capability],
            "metadata": {
                k: v for k, v in metadata.items() 
                if k in ["description", "author", "license", "created_at", "updated_at"]
            }
        }
    
    def _remove_from_index(self, cell_id: str):
        """
        Remove a cell from the index.
        
        Args:
            cell_id: Unique identifier for the cell
        """
        # Check if cell exists in index
        if cell_id not in self.index["by_id"]:
            return
        
        # Get cell information
        cell_info = self.index["by_id"][cell_id]
        cell_type = cell_info.get("cell_type")
        capability = cell_info.get("capability")
        version = cell_info.get("version", "latest")
        
        # Remove from ID index
        del self.index["by_id"][cell_id]
        
        # Remove from type index
        if cell_type in self.index["by_type"] and version in self.index["by_type"][cell_type]:
            if self.index["by_type"][cell_type][version] == cell_id:
                del self.index["by_type"][cell_type][version]
            
            # If no versions left, remove the cell type
            if not self.index["by_type"][cell_type]:
                del self.index["by_type"][cell_type]
        
        # Remove from capability index
        if capability in self.index["by_capability"]:
            if cell_id in self.index["by_capability"][capability]:
                self.index["by_capability"][capability].remove(cell_id)
            
            # If no cells left for this capability, remove it
            if not self.index["by_capability"][capability]:
                del self.index["by_capability"][capability]
        
        # Remove from version index
        version_key = f"{cell_type}:{version}"
        if version_key in self.index["by_version"]:
            del self.index["by_version"][version_key]
        
        # Update capabilities map
        self._rebuild_capabilities_map()
        
        # Update cell types map
        if cell_type in self.cell_types:
            # Check if this is the only cell of this type
            other_versions = [
                cid for cid, info in self.index["by_id"].items()
                if info.get("cell_type") == cell_type and cid != cell_id
            ]
            
            if not other_versions:
                del self.cell_types[cell_type]
            else:
                # Update latest version
                latest_version = max([
                    self.index["by_id"][cid].get("version", "0.0.0")
                    for cid in other_versions
                ], key=self._version_key)
                
                self.cell_types[cell_type]["latest_version"] = latest_version
    
    def _rebuild_capabilities_map(self):
        """Rebuild the capabilities map from the current index."""
        self.capabilities = {}
        
        for cell_id, cell_info in self.index["by_id"].items():
            capability = cell_info.get("capability")
            cell_type = cell_info.get("cell_type")
            
            if capability and cell_type:
                if capability not in self.capabilities:
                    self.capabilities[capability] = []
                
                if cell_type not in self.capabilities[capability]:
                    self.capabilities[capability].append(cell_type)
    
    def _version_key(self, version: str) -> Tuple:
        """
        Convert a version string to a tuple for sorting.
        
        Args:
            version: Version string (e.g., "1.2.3")
            
        Returns:
            Tuple representation for sorting
        """
        if version == "latest":
            return (float('inf'), float('inf'), float('inf'))
        
        parts = version.split('.')
        result = []
        
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                # Handle non-numeric version parts
                result.append(0)
        
        # Ensure we have at least 3 parts
        while len(result) < 3:
            result.append(0)
        
        return tuple(result)
    
    async def get_cell_by_id(self, cell_id: str) -> Dict[str, Any]:
        """
        Retrieve a cell by its ID.
        
        Args:
            cell_id: Unique identifier for the cell
            
        Returns:
            Cell metadata
            
        Raises:
            CellNotFoundError: If the cell is not found
        """
        self.total_retrievals += 1
        
        # Check cache first
        if self.cache_enabled and cell_id in self.cell_cache:
            self.cache_hits += 1
            self.cache_access_times[cell_id] = time.time()
            return self.cell_cache[cell_id]
        
        # Check if cell exists in index
        if cell_id not in self.index["by_id"]:
            raise CellNotFoundError(f"Cell not found: {cell_id}")
        
        try:
            # Load cell metadata
            metadata_path = os.path.join(self.storage_path, "metadata", f"{cell_id}.json")
            
            if not os.path.exists(metadata_path):
                raise CellNotFoundError(f"Cell metadata not found: {cell_id}")
            
            async with aiofiles.open(metadata_path, 'r') as f:
                metadata = json.loads(await f.read())
            
            # Add to cache
            if self.cache_enabled:
                self._add_to_cache(cell_id, metadata)
            
            return metadata
            
        except CellNotFoundError:
            raise
            
        except Exception as e:
            logger.error(f"Error retrieving cell {cell_id}: {e}", exc_info=True)
            raise RepositoryError(f"Failed to retrieve cell: {e}")
    
    async def get_cell_by_type(
        self, 
        cell_type: str, 
        version: str = "latest",
        raise_error: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve a cell by its type and version.
        
        Args:
            cell_type: Type of cell to retrieve
            version: Version of the cell (default: "latest")
            raise_error: Whether to raise an error if cell not found
            
        Returns:
            Cell metadata
            
        Raises:
            CellNotFoundError: If the cell is not found and raise_error is True
        """
        self.total_retrievals += 1
        
        # Determine version to use
        if version == "latest":
            # Get latest version from cell types map
            if cell_type in self.cell_types:
                version = self.cell_types[cell_type].get("latest_version", "latest")
        
        # Check index for the cell
        if cell_type not in self.index["by_type"]:
            if raise_error:
                raise CellNotFoundError(f"Cell type not found: {cell_type}")
            return None
        
        if version not in self.index["by_type"][cell_type]:
            if raise_error:
                raise CellNotFoundError(f"Version {version} not found for cell type {cell_type}")
            return None
        
        # Get cell ID from index
        cell_id = self.index["by_type"][cell_type][version]
        
        # Retrieve cell by ID
        return await self.get_cell_by_id(cell_id)
    
    async def get_cell_for_capability(
        self, 
        capability: str, 
        parameters: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Find the best cell for a given capability and context.
        
        Args:
            capability: Required capability
            parameters: Capability parameters
            context: Request context
            
        Returns:
            Cell metadata
            
        Raises:
            CellNotFoundError: If no suitable cell is found
        """
        self.total_retrievals += 1
        
        # Check if capability exists
        if capability not in self.index["by_capability"]:
            raise CellNotFoundError(f"Capability not found: {capability}")
        
        # Get all cells with this capability
        cell_ids = self.index["by_capability"][capability]
        
        if not cell_ids:
            raise CellNotFoundError(f"No cells available for capability: {capability}")
        
        # In a real implementation, we would use machine learning or heuristics
        # to find the best cell based on parameters and context.
        # For this example, we'll use a simple algorithm.
        
        # Load metadata for all matching cells
        cells = []
        for cell_id in cell_ids:
            try:
                cell = await self.get_cell_by_id(cell_id)
                cells.append(cell)
            except Exception as e:
                logger.warning(f"Error loading cell {cell_id}: {e}")
        
        if not cells:
            raise CellNotFoundError(f"No valid cells found for capability: {capability}")
        
        # Score cells based on fitness for the request
        scores = {}
        
        for cell in cells:
            score = self._score_cell_fitness(cell, capability, parameters, context)
            scores[cell["id"]] = score
        
        # Get the cell with the highest score
        best_cell_id = max(scores, key=scores.get)
        best_cell = next(cell for cell in cells if cell["id"] == best_cell_id)
        
        logger.info(f"Selected cell {best_cell_id} with score {scores[best_cell_id]} for capability {capability}")
        
        return best_cell
    
    def _score_cell_fitness(
        self, 
        cell: Dict[str, Any], 
        capability: str,
        parameters: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> float:
        """
        Score a cell's fitness for a capability request.
        
        Args:
            cell: Cell metadata
            capability: Required capability
            parameters: Capability parameters
            context: Request context
            
        Returns:
            Fitness score (higher is better)
        """
        # Start with a base score
        score = 1.0
        
        # In a real implementation, this would use more sophisticated scoring
        # based on:
        # - Parameter compatibility
        # - Context compatibility (device, resources, etc.)
        # - Performance history
        # - User preferences
        # - Quantum trail patterns
        
        # Example scoring factors:
        
        # 1. Version recency (newer versions score higher)
        version = cell.get("version", "1.0.0")
        if version != "latest":
            version_parts = [int(p) for p in version.split(".")]
            version_score = version_parts[0] + version_parts[1]/100
            score *= (1 + version_score / 10)  # Slight boost for newer versions
        
        # 2. Resource requirements (lower is better)
        resources = cell.get("resource_requirements", {})
        memory_mb = resources.get("memory_mb", 100)
        cpu_percent = resources.get("cpu_percent", 10)
        
        # Adjust score based on resource requirements
        resource_factor = 1.0
        if context and "device_info" in context:
            device_memory = context["device_info"].get("memory_gb", 8) * 1024
            device_cpu = context["device_info"].get("cpu_cores", 4) * 25  # Approximate % per core
            
            # Resource compatibility
            if memory_mb > device_memory * 0.8:
                resource_factor *= 0.5  # Penalize if close to device limits
            if cpu_percent > device_cpu * 0.8:
                resource_factor *= 0.5
        
        score *= resource_factor
        
        # 3. Parameter compatibility
        if parameters and "cell_parameters" in cell:
            cell_params = cell.get("cell_parameters", {})
            matched_params = sum(1 for p in parameters if p in cell_params)
            param_score = matched_params / max(1, len(parameters))
            score *= (0.5 + param_score)  # Scale between 0.5 and 1.5
        
        # 4. Specialization score (specific implementations score higher)
        if cell.get("specialized_contexts", []) and context:
            specialized_for = cell.get("specialized_contexts", [])
            context_type = context.get("environment", {}).get("type", "")
            if context_type in specialized_for:
                score *= 1.5  # Significant boost for specialized cells
        
        # 5. Usage metrics (if available)
        metrics = cell.get("usage_metrics", {})
        success_rate = metrics.get("success_rate", 0.9)
        score *= success_rate
        
        return score
    
    async def get_cell_package(self, cell_id: str) -> Dict[str, Any]:
        """
        Retrieve a cell package.
        
        Args:
            cell_id: Unique identifier for the cell
            
        Returns:
            Cell package data
            
        Raises:
            CellNotFoundError: If the cell package is not found
        """
        # Check if cell exists in index
        if cell_id not in self.index["by_id"]:
            raise CellNotFoundError(f"Cell not found: {cell_id}")
        
        try:
            # Load cell package
            package_path = os.path.join(self.storage_path, "packages", f"{cell_id}.package")
            
            if not os.path.exists(package_path):
                raise CellNotFoundError(f"Cell package not found: {cell_id}")
            
            async with aiofiles.open(package_path, 'rb') as f:
                package_data = await f.read()
            
            # In a real implementation, the package might be compressed or encoded
            # Here we'll assume it's a JSON string
            try:
                package = json.loads(package_data)
                return package
            except json.JSONDecodeError:
                # If not JSON, return as base64
                import base64
                return {
                    "format": "binary",
                    "data": base64.b64encode(package_data).decode('utf-8')
                }
            
        except CellNotFoundError:
            raise
            
        except Exception as e:
            logger.error(f"Error retrieving cell package {cell_id}: {e}", exc_info=True)
            raise RepositoryError(f"Failed to retrieve cell package: {e}")
    
    async def register_cell(
        self,
        cell_type: str,
        capability: str,
        version: str,
        package: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Register a new cell in the repository.
        
        Args:
            cell_type: Type of cell
            capability: Cell capability
            version: Cell version
            package: Cell package data
            metadata: Additional cell metadata
            
        Returns:
            Cell ID
            
        Raises:
            RepositoryError: If registration fails
        """
        self.total_registrations += 1
        
        try:
            # Generate cell ID
            cell_id = str(uuid.uuid4())
            
            # Prepare metadata
            metadata = metadata or {}
            
            cell_metadata = {
                "id": cell_id,
                "cell_type": cell_type,
                "capability": capability,
                "version": version,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                **metadata
            }
            
            # Save metadata
            metadata_path = os.path.join(self.storage_path, "metadata", f"{cell_id}.json")
            
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(cell_metadata, indent=2))
            
            # Save package
            package_path = os.path.join(self.storage_path, "packages", f"{cell_id}.package")
            
            async with aiofiles.open(package_path, 'w') as f:
                if isinstance(package, dict):
                    await f.write(json.dumps(package))
                else:
                    await f.write(package)
            
            # Add to index
            self._add_to_index(cell_id, cell_metadata)
            
            # Save index
            await self._save_index()
            
            logger.info(f"Registered cell {cell_id} of type {cell_type} version {version}")
            
            return cell_id
            
        except Exception as e:
            logger.error(f"Error registering cell: {e}", exc_info=True)
            raise RepositoryError(f"Failed to register cell: {e}")
    
    async def update_cell(self, cell_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing cell.
        
        Args:
            cell_id: Unique identifier for the cell
            updates: Cell updates
            
        Returns:
            Updated cell metadata
            
        Raises:
            CellNotFoundError: If the cell is not found
            RepositoryError: If update fails
        """
        try:
            # Get existing cell metadata
            existing_cell = await self.get_cell_by_id(cell_id)
            
            # Apply updates
            cell_metadata = {**existing_cell, **updates}
            
            # Update timestamp
            cell_metadata["updated_at"] = datetime.now().isoformat()
            
            # Save metadata
            metadata_path = os.path.join(self.storage_path, "metadata", f"{cell_id}.json")
            
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(cell_metadata, indent=2))
            
            # Update package if provided
            if "package" in updates:
                package_path = os.path.join(self.storage_path, "packages", f"{cell_id}.package")
                
                async with aiofiles.open(package_path, 'w') as f:
                    if isinstance(updates["package"], dict):
                        await f.write(json.dumps(updates["package"]))
                    else:
                        await f.write(updates["package"])
                
                # Remove package from metadata
                if "package" in cell_metadata:
                    del cell_metadata["package"]
            
            # Update index
            self._remove_from_index(cell_id)
            self._add_to_index(cell_id, cell_metadata)
            
            # Save index
            await self._save_index()
            
            # Update cache
            if self.cache_enabled and cell_id in self.cell_cache:
                self.cell_cache[cell_id] = cell_metadata
                self.cache_access_times[cell_id] = time.time()
            
            logger.info(f"Updated cell {cell_id}")
            
            return cell_metadata
            
        except CellNotFoundError:
            raise
            
        except Exception as e:
            logger.error(f"Error updating cell {cell_id}: {e}", exc_info=True)
            raise RepositoryError(f"Failed to update cell: {e}")
    
    async def remove_cell(self, cell_id: str) -> bool:
        """
        Remove a cell from the repository.
        
        Args:
            cell_id: Unique identifier for the cell
            
        Returns:
            True if cell was removed, False otherwise
            
        Raises:
            CellNotFoundError: If the cell is not found
            RepositoryError: If removal fails
        """
        try:
            # Check if cell exists in index
            if cell_id not in self.index["by_id"]:
                raise CellNotFoundError(f"Cell not found: {cell_id}")
            
            # Remove metadata file
            metadata_path = os.path.join(self.storage_path, "metadata", f"{cell_id}.json")
            
            if await aio_os.path.exists(metadata_path):
                await aio_os.remove(metadata_path)
            
            # Remove package file
            package_path = os.path.join(self.storage_path, "packages", f"{cell_id}.package")
            
            if await aio_os.path.exists(package_path):
                await aio_os.remove(package_path)
            
            # Remove from index
            self._remove_from_index(cell_id)
            
            # Save index
            await self._save_index()
            
            # Remove from cache
            if self.cache_enabled and cell_id in self.cell_cache:
                del self.cell_cache[cell_id]
                if cell_id in self.cache_access_times:
                    del self.cache_access_times[cell_id]
            
            logger.info(f"Removed cell {cell_id}")
            
            return True
            
        except CellNotFoundError:
            raise
            
        except Exception as e:
            logger.error(f"Error removing cell {cell_id}: {e}", exc_info=True)
            raise RepositoryError(f"Failed to remove cell: {e}")
    
    async def get_capabilities(self) -> Dict[str, List[str]]:
        """
        Get all available capabilities in the repository.
        
        Returns:
            Dictionary mapping capabilities to cell types
        """
        # Return a copy to prevent modification
        return self.capabilities.copy()
    
    def get_capability_description(self, capability: str) -> str:
        """
        Get the description for a capability.
        
        Args:
            capability: Capability name
            
        Returns:
            Capability description
        """
        # Check if capability exists
        if capability not in self.capabilities:
            return "Unknown capability"
        
        # In a real implementation, we would store capability descriptions
        # Here we'll generate a generic one
        return f"Provides {capability} functionality"
    
    def get_capability_versions(self, capability: str) -> List[str]:
        """
        Get available versions for a capability.
        
        Args:
            capability: Capability name
            
        Returns:
            List of available versions
        """
        versions = []
        
        # Check if capability exists
        if capability not in self.capabilities:
            return versions
        
        # Get all cell types for this capability
        cell_types = self.capabilities[capability]
        
        # Get versions for each cell type
        for cell_type in cell_types:
            if cell_type in self.index["by_type"]:
                versions.extend(list(self.index["by_type"][cell_type].keys()))
        
        # Remove duplicates and sort
        versions = list(set(versions))
        versions.sort(key=self._version_key, reverse=True)
        
        return versions
    
    def _add_to_cache(self, cell_id: str, cell_data: Dict[str, Any]):
        """
        Add a cell to the in-memory cache.
        
        Args:
            cell_id: Unique identifier for the cell
            cell_data: Cell data to cache
        """
        if not self.cache_enabled:
            return
        
        # Add to cache
        self.cell_cache[cell_id] = cell_data
        self.cache_access_times[cell_id] = time.time()
        
        # Check cache size
        if len(self.cell_cache) > self.cache_max_size:
            # Remove least recently used
            oldest = min(self.cache_access_times.items(), key=lambda x: x[1])
            del self.cell_cache[oldest[0]]
            del self.cache_access_times[oldest[0]]
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get repository status information.
        
        Returns:
            Status information
        """
        # Calculate uptime
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate cache hit rate
        if self.total_retrievals > 0:
            cache_hit_rate = (self.cache_hits / self.total_retrievals) * 100
        else:
            cache_hit_rate = 0
        
        # Get storage usage
        storage_usage = await self._get_storage_usage()
        
        return {
            "repo_id": self.repo_id,
            "status": "active",
            "uptime_seconds": uptime_seconds,
            "total_cells": len(self.index["by_id"]),
            "total_capabilities": len(self.capabilities),
            "total_cell_types": len(self.cell_types),
            "total_retrievals": self.total_retrievals,
            "total_registrations": self.total_registrations,
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self.cell_cache),
            "cache_hit_rate": cache_hit_rate,
            "storage_usage_mb": storage_usage
        }
    
    async def _get_storage_usage(self) -> float:
        """
        Calculate storage usage in MB.
        
        Returns:
            Storage usage in MB
        """
        total_size = 0
        
        try:
            # Check metadata size
            metadata_dir = os.path.join(self.storage_path, "metadata")
            if os.path.exists(metadata_dir):
                for filename in os.listdir(metadata_dir):
                    file_path = os.path.join(metadata_dir, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            
            # Check packages size
            packages_dir = os.path.join(self.storage_path, "packages")
            if os.path.exists(packages_dir):
                for filename in os.listdir(packages_dir):
                    file_path = os.path.join(packages_dir, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            
            # Check index size
            index_dir = os.path.join(self.storage_path, "index")
            if os.path.exists(index_dir):
                for filename in os.listdir(index_dir):
                    file_path = os.path.join(index_dir, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
            
            # Convert to MB
            total_size_mb = total_size / (1024 * 1024)
            return total_size_mb
            
        except Exception as e:
            logger.error(f"Error calculating storage usage: {e}")
            return 0
    
    async def backup_repository(self, backup_path: str = None) -> str:
        """
        Create a backup of the repository.
        
        Args:
            backup_path: Path to store the backup
            
        Returns:
            Path to the backup
        """
        if not backup_path:
            backup_path = f"{self.storage_path}_backup_{int(time.time())}"
        
        try:
            # Ensure backup directory exists
            os.makedirs(backup_path, exist_ok=True)
            
            # Copy metadata directory
            metadata_src = os.path.join(self.storage_path, "metadata")
            metadata_dst = os.path.join(backup_path, "metadata")
            
            if os.path.exists(metadata_src):
                os.makedirs(metadata_dst, exist_ok=True)
                for file in os.listdir(metadata_src):
                    shutil.copy2(
                        os.path.join(metadata_src, file),
                        os.path.join(metadata_dst, file)
                    )
            
            # Copy packages directory
            packages_src = os.path.join(self.storage_path, "packages")
            packages_dst = os.path.join(backup_path, "packages")
            
            if os.path.exists(packages_src):
                os.makedirs(packages_dst, exist_ok=True)
                for file in os.listdir(packages_src):
                    shutil.copy2(
                        os.path.join(packages_src, file),
                        os.path.join(packages_dst, file)
                    )
            
            # Copy index directory
            index_src = os.path.join(self.storage_path, "index")
            index_dst = os.path.join(backup_path, "index")
            
            if os.path.exists(index_src):
                os.makedirs(index_dst, exist_ok=True)
                for file in os.listdir(index_src):
                    shutil.copy2(
                        os.path.join(index_src, file),
                        os.path.join(index_dst, file)
                    )
            
            logger.info(f"Repository backup created at {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating repository backup: {e}", exc_info=True)
            raise RepositoryError(f"Failed to create repository backup: {e}")
    
    async def restore_repository(self, backup_path: str) -> bool:
        """
        Restore the repository from a backup.
        
        Args:
            backup_path: Path to the backup
            
        Returns:
            True if restore was successful
            
        Raises:
            RepositoryError: If restore fails
        """
        try:
            # Check if backup exists
            if not os.path.exists(backup_path):
                raise RepositoryError(f"Backup not found: {backup_path}")
            
            # Create backup of current repository
            if self.config.get("backup_before_restore", True):
                await self.backup_repository()
            
            # Clear current repository
            await self._clear_repository()
            
            # Copy metadata directory
            metadata_src = os.path.join(backup_path, "metadata")
            metadata_dst = os.path.join(self.storage_path, "metadata")
            
            if os.path.exists(metadata_src):
                os.makedirs(metadata_dst, exist_ok=True)
                for file in os.listdir(metadata_src):
                    shutil.copy2(
                        os.path.join(metadata_src, file),
                        os.path.join(metadata_dst, file)
                    )
            
            # Copy packages directory
            packages_src = os.path.join(backup_path, "packages")
            packages_dst = os.path.join(self.storage_path, "packages")
            
            if os.path.exists(packages_src):
                os.makedirs(packages_dst, exist_ok=True)
                for file in os.listdir(packages_src):
                    shutil.copy2(
                        os.path.join(packages_src, file),
                        os.path.join(packages_dst, file)
                    )
            
            # Copy index directory
            index_src = os.path.join(backup_path, "index")
            index_dst = os.path.join(self.storage_path, "index")
            
            if os.path.exists(index_src):
                os.makedirs(index_dst, exist_ok=True)
                for file in os.listdir(index_src):
                    shutil.copy2(
                        os.path.join(index_src, file),
                        os.path.join(index_dst, file)
                    )
            
            # Reload index
            await self._load_index()
            
            logger.info(f"Repository restored from {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring repository: {e}", exc_info=True)
            raise RepositoryError(f"Failed to restore repository: {e}")
    
    async def _clear_repository(self):
        """
        Clear all data from the repository.
        
        Note: This does not delete the repository directories.
        """
        try:
            # Clear metadata directory
            metadata_dir = os.path.join(self.storage_path, "metadata")
            if os.path.exists(metadata_dir):
                for file in os.listdir(metadata_dir):
                    os.remove(os.path.join(metadata_dir, file))
            
            # Clear packages directory
            packages_dir = os.path.join(self.storage_path, "packages")
            if os.path.exists(packages_dir):
                for file in os.listdir(packages_dir):
                    os.remove(os.path.join(packages_dir, file))
            
            # Clear index directory
            index_dir = os.path.join(self.storage_path, "index")
            if os.path.exists(index_dir):
                for file in os.listdir(index_dir):
                    os.remove(os.path.join(index_dir, file))
            
            # Reset in-memory structures
            self.index = {
                "by_id": {},
                "by_type": {},
                "by_capability": {},
                "by_version": {}
            }
            
            self.capabilities = {}
            self.cell_types = {}
            
            # Clear cache
            self.cell_cache.clear()
            self.cache_access_times.clear()
            
        except Exception as e:
            logger.error(f"Error clearing repository: {e}", exc_info=True)
            raise RepositoryError(f"Failed to clear repository: {e}")

# Convenience function to create and configure a repository manager
async def create_repository_manager(
    storage_path: str = None,
    config_path: str = None
) -> RepositoryManager:
    """
    Create and configure a Repository Manager instance.
    
    Args:
        storage_path: Path to the repository storage
        config_path: Path to configuration file
        
    Returns:
        Configured RepositoryManager instance
    """
    # Load configuration
    config = {}
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            logger.warning("Using default configuration")
    
    # Create repository manager
    manager = RepositoryManager(storage_path, config)
    
    # Initialize
    await manager.initialize()
    
    return manager

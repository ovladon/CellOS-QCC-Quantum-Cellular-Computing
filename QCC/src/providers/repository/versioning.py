"""
Cell versioning system for Quantum Cellular Computing.

This module provides functionality for managing cell versions within the repository,
including version tracking, comparison, and compatibility verification. It enables
the repository to maintain multiple versions of cells while ensuring appropriate
version selection based on compatibility requirements.
"""

import os
import re
import logging
import semver
import json
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from datetime import datetime
from dataclasses import dataclass

from qcc.common.exceptions import VersionError, CompatibilityError
from qcc.providers.repository.storage import StorageManager

logger = logging.getLogger(__name__)

@dataclass
class VersionInfo:
    """
    Information about a specific cell version.
    
    Attributes:
        version: Semantic version string (e.g., "1.2.3")
        cell_id: Unique identifier of the cell
        hash: Content hash for integrity verification
        created_at: Timestamp when this version was created
        author: Author of this version
        required_capabilities: Capabilities required by this version
        provided_capabilities: Capabilities provided by this version
        dependencies: Other cells this version depends on
        compatibility: Compatibility information with other versions
        release_notes: Notes describing changes in this version
        metadata: Additional metadata for this version
    """
    version: str
    cell_id: str
    hash: str
    created_at: datetime
    author: str
    required_capabilities: List[str]
    provided_capabilities: Dict[str, str]  # capability_name: version
    dependencies: Dict[str, str]  # cell_id: version_constraint
    compatibility: Dict[str, List[str]]  # cell_id: [compatible_version_constraints]
    release_notes: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "cell_id": self.cell_id,
            "hash": self.hash,
            "created_at": self.created_at.isoformat(),
            "author": self.author,
            "required_capabilities": self.required_capabilities,
            "provided_capabilities": self.provided_capabilities,
            "dependencies": self.dependencies,
            "compatibility": self.compatibility,
            "release_notes": self.release_notes,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionInfo':
        """Create VersionInfo from dictionary."""
        # Convert ISO format string back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        return cls(
            version=data.get("version", "0.0.0"),
            cell_id=data.get("cell_id", ""),
            hash=data.get("hash", ""),
            created_at=data.get("created_at", datetime.now()),
            author=data.get("author", ""),
            required_capabilities=data.get("required_capabilities", []),
            provided_capabilities=data.get("provided_capabilities", {}),
            dependencies=data.get("dependencies", {}),
            compatibility=data.get("compatibility", {}),
            release_notes=data.get("release_notes", ""),
            metadata=data.get("metadata", {})
        )


class VersionManager:
    """
    Manages cell versioning within the repository.
    
    This class provides functionality for tracking cell versions, checking compatibility,
    and selecting appropriate versions based on constraints.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Initialize the version manager.
        
        Args:
            storage_manager: Storage manager for accessing cell data
        """
        self.storage_manager = storage_manager
        self.version_cache = {}  # cell_id -> {version -> VersionInfo}
        
    async def register_version(self, cell_data: Dict[str, Any], version_info: Dict[str, Any] = None) -> VersionInfo:
        """
        Register a new cell version in the repository.
        
        Args:
            cell_data: Cell data including manifest and code
            version_info: Additional version information
            
        Returns:
            Version information for the registered cell
            
        Raises:
            VersionError: If the version is invalid or already exists
        """
        if not cell_data:
            raise VersionError("Cannot register empty cell data")
            
        # Extract cell manifest
        manifest = cell_data.get("manifest", {})
        if not manifest:
            raise VersionError("Cell manifest is required")
            
        cell_id = manifest.get("id", "")
        if not cell_id:
            raise VersionError("Cell ID is required in manifest")
            
        version_str = manifest.get("version", "")
        if not version_str:
            raise VersionError("Version is required in manifest")
            
        try:
            # Validate version string (will raise ValueError if invalid)
            semver.VersionInfo.parse(version_str)
        except ValueError as e:
            raise VersionError(f"Invalid version format (must be semver): {e}")
            
        # Check if this version already exists
        if await self.version_exists(cell_id, version_str):
            raise VersionError(f"Version {version_str} already exists for cell {cell_id}")
            
        # Generate content hash for integrity verification
        content_hash = self._generate_content_hash(cell_data)
        
        # Create version info
        version_info = VersionInfo(
            version=version_str,
            cell_id=cell_id,
            hash=content_hash,
            created_at=datetime.now(),
            author=manifest.get("author", "unknown"),
            required_capabilities=manifest.get("required_capabilities", []),
            provided_capabilities=manifest.get("capabilities", {}),
            dependencies=manifest.get("dependencies", {}),
            compatibility=manifest.get("compatibility", {}),
            release_notes=version_info.get("release_notes", "") if version_info else "",
            metadata=version_info.get("metadata", {}) if version_info else {}
        )
        
        # Save cell data with version information
        await self._save_version(cell_id, version_str, cell_data, version_info)
        
        # Update version cache
        self._update_cache(cell_id, version_str, version_info)
        
        logger.info(f"Registered cell {cell_id} version {version_str}")
        return version_info
    
    async def get_version(self, cell_id: str, version: str = "latest") -> VersionInfo:
        """
        Get version information for a cell.
        
        Args:
            cell_id: Cell identifier
            version: Version string or "latest"
            
        Returns:
            Version information
            
        Raises:
            VersionError: If the version does not exist
        """
        # Check cache first
        if cell_id in self.version_cache and version in self.version_cache[cell_id]:
            return self.version_cache[cell_id][version]
            
        # Resolve "latest" to actual version
        if version == "latest":
            actual_version = await self.get_latest_version(cell_id)
            if not actual_version:
                raise VersionError(f"No versions found for cell {cell_id}")
            version = actual_version
        
        try:
            # Load version info from storage
            version_path = self._get_version_info_path(cell_id, version)
            version_data = await self.storage_manager.read_json(version_path)
            
            if not version_data:
                raise VersionError(f"Version {version} not found for cell {cell_id}")
                
            version_info = VersionInfo.from_dict(version_data)
            
            # Update cache
            self._update_cache(cell_id, version, version_info)
            
            return version_info
            
        except Exception as e:
            logger.error(f"Error getting version {version} for cell {cell_id}: {e}")
            raise VersionError(f"Failed to get version information: {str(e)}")
    
    async def get_latest_version(self, cell_id: str) -> Optional[str]:
        """
        Get the latest version for a cell.
        
        Args:
            cell_id: Cell identifier
            
        Returns:
            Latest version string or None if no versions exist
        """
        versions = await self.list_versions(cell_id)
        if not versions:
            return None
            
        # Sort versions semantically
        sorted_versions = sorted(versions, key=lambda v: semver.VersionInfo.parse(v), reverse=True)
        return sorted_versions[0]
    
    async def list_versions(self, cell_id: str) -> List[str]:
        """
        List all available versions for a cell.
        
        Args:
            cell_id: Cell identifier
            
        Returns:
            List of version strings
        """
        try:
            # Get versions directory for this cell
            versions_dir = os.path.join(self._get_cell_path(cell_id), "versions")
            
            # List directories, each representing a version
            version_dirs = await self.storage_manager.list_directories(versions_dir)
            
            # Extract version from directory names
            versions = []
            for dir_name in version_dirs:
                # Validate that the directory name is a valid semver
                try:
                    semver.VersionInfo.parse(dir_name)
                    versions.append(dir_name)
                except ValueError:
                    logger.warning(f"Ignoring invalid version directory: {dir_name}")
            
            return versions
            
        except Exception as e:
            logger.error(f"Error listing versions for cell {cell_id}: {e}")
            return []
    
    async def version_exists(self, cell_id: str, version: str) -> bool:
        """
        Check if a specific version exists for a cell.
        
        Args:
            cell_id: Cell identifier
            version: Version string
            
        Returns:
            True if the version exists, False otherwise
        """
        try:
            # Check if version info file exists
            version_path = self._get_version_info_path(cell_id, version)
            return await self.storage_manager.exists(version_path)
        except Exception as e:
            logger.error(f"Error checking version existence for cell {cell_id} version {version}: {e}")
            return False
    
    async def get_matching_version(self, cell_id: str, version_constraint: str) -> Optional[str]:
        """
        Get the latest version matching a constraint.
        
        Args:
            cell_id: Cell identifier
            version_constraint: Version constraint (e.g., ">=1.0.0 <2.0.0")
            
        Returns:
            Matching version string or None if no match
        """
        versions = await self.list_versions(cell_id)
        if not versions:
            return None
            
        # Filter versions matching the constraint
        matching_versions = []
        for version in versions:
            try:
                if semver.match(version, version_constraint):
                    matching_versions.append(version)
            except ValueError as e:
                logger.warning(f"Invalid version constraint {version_constraint}: {e}")
                # If constraint is invalid, try exact match
                if version == version_constraint:
                    matching_versions.append(version)
        
        if not matching_versions:
            return None
            
        # Return latest matching version
        sorted_versions = sorted(matching_versions, key=lambda v: semver.VersionInfo.parse(v), reverse=True)
        return sorted_versions[0]
    
    async def check_compatibility(self, cell_id: str, version: str, target_cell_id: str, target_version: str) -> bool:
        """
        Check if two cell versions are compatible.
        
        Args:
            cell_id: First cell identifier
            version: First cell version
            target_cell_id: Second cell identifier
            target_version: Second cell version
            
        Returns:
            True if the cells are compatible, False otherwise
        """
        try:
            # Get version info for first cell
            version_info = await self.get_version(cell_id, version)
            
            # Check compatibility information
            compatibility = version_info.compatibility
            if target_cell_id in compatibility:
                constraints = compatibility[target_cell_id]
                for constraint in constraints:
                    if semver.match(target_version, constraint):
                        return True
                
                # No matching constraint
                return False
            
            # No compatibility information specified, assume compatible
            return True
            
        except Exception as e:
            logger.error(f"Error checking compatibility between {cell_id} v{version} and {target_cell_id} v{target_version}: {e}")
            return False
    
    async def get_cell_data(self, cell_id: str, version: str = "latest") -> Dict[str, Any]:
        """
        Get the full cell data for a specific version.
        
        Args:
            cell_id: Cell identifier
            version: Version string or "latest"
            
        Returns:
            Cell data including code and manifest
            
        Raises:
            VersionError: If the version does not exist
        """
        # Resolve "latest" to actual version
        if version == "latest":
            actual_version = await self.get_latest_version(cell_id)
            if not actual_version:
                raise VersionError(f"No versions found for cell {cell_id}")
            version = actual_version
        
        try:
            # Get cell data path
            cell_path = os.path.join(self._get_cell_version_path(cell_id, version), "cell_data.json")
            
            # Read cell data
            cell_data = await self.storage_manager.read_json(cell_path)
            
            if not cell_data:
                raise VersionError(f"Cell data not found for {cell_id} version {version}")
                
            return cell_data
            
        except Exception as e:
            logger.error(f"Error getting cell data for {cell_id} version {version}: {e}")
            raise VersionError(f"Failed to get cell data: {str(e)}")
    
    async def resolve_dependencies(
        self, 
        cell_id: str, 
        version: str = "latest"
    ) -> Dict[str, str]:
        """
        Resolve all dependencies for a cell version.
        
        Args:
            cell_id: Cell identifier
            version: Version string or "latest"
            
        Returns:
            Dictionary mapping cell_id to resolved version
            
        Raises:
            CompatibilityError: If dependencies cannot be resolved
        """
        # Get version info
        version_info = await self.get_version(cell_id, version)
        
        # Initialize result with this cell
        resolved = {cell_id: version_info.version}
        
        # Process dependencies
        dependencies = version_info.dependencies.copy()
        
        # Breadth-first resolution to avoid deep recursion
        visited = set([cell_id])
        pending = [(dep_id, constraint) for dep_id, constraint in dependencies.items()]
        
        while pending:
            dep_id, constraint = pending.pop(0)
            
            # Skip if already resolved
            if dep_id in resolved:
                continue
                
            # Find matching version
            matching_version = await self.get_matching_version(dep_id, constraint)
            if not matching_version:
                raise CompatibilityError(f"No version of {dep_id} matches constraint {constraint}")
                
            # Check compatibility with already resolved dependencies
            for resolved_id, resolved_version in resolved.items():
                if not await self.check_compatibility(dep_id, matching_version, resolved_id, resolved_version):
                    raise CompatibilityError(
                        f"Dependency conflict: {dep_id} v{matching_version} is not compatible with "
                        f"{resolved_id} v{resolved_version}"
                    )
            
            # Add to resolved
            resolved[dep_id] = matching_version
            visited.add(dep_id)
            
            # Get transitive dependencies
            dep_info = await self.get_version(dep_id, matching_version)
            for trans_dep_id, trans_constraint in dep_info.dependencies.items():
                if trans_dep_id not in visited:
                    pending.append((trans_dep_id, trans_constraint))
        
        return resolved
    
    async def create_upgrade_path(self, cell_id: str, from_version: str, to_version: str) -> List[str]:
        """
        Create a version upgrade path between two versions.
        
        Args:
            cell_id: Cell identifier
            from_version: Starting version
            to_version: Target version
            
        Returns:
            List of version strings representing the upgrade path
            
        Raises:
            VersionError: If no valid upgrade path can be constructed
        """
        # Validate versions
        if not await self.version_exists(cell_id, from_version):
            raise VersionError(f"Starting version {from_version} does not exist for cell {cell_id}")
            
        if not await self.version_exists(cell_id, to_version):
            raise VersionError(f"Target version {to_version} does not exist for cell {cell_id}")
            
        # Parse versions
        from_ver = semver.VersionInfo.parse(from_version)
        to_ver = semver.VersionInfo.parse(to_version)
        
        # If versions are the same, return single-element path
        if from_ver == to_ver:
            return [from_version]
            
        # If downgrading
        if from_ver > to_ver:
            return await self._create_downgrade_path(cell_id, from_version, to_version)
            
        # Get all versions
        all_versions = await self.list_versions(cell_id)
        
        # Sort versions between from_version and to_version
        relevant_versions = []
        for version in all_versions:
            ver = semver.VersionInfo.parse(version)
            if from_ver <= ver <= to_ver:
                relevant_versions.append(version)
                
        if not relevant_versions:
            raise VersionError(f"No versions found between {from_version} and {to_version}")
            
        # Sort by semver
        path = sorted(relevant_versions, key=lambda v: semver.VersionInfo.parse(v))
        
        # Ensure from_version is first and to_version is last
        if path[0] != from_version:
            path.insert(0, from_version)
        if path[-1] != to_version:
            path.append(to_version)
            
        return path
    
    async def _create_downgrade_path(self, cell_id: str, from_version: str, to_version: str) -> List[str]:
        """
        Create a version downgrade path between two versions.
        
        Args:
            cell_id: Cell identifier
            from_version: Starting version (higher)
            to_version: Target version (lower)
            
        Returns:
            List of version strings representing the downgrade path
        """
        # Get all versions
        all_versions = await self.list_versions(cell_id)
        
        # Parse versions
        from_ver = semver.VersionInfo.parse(from_version)
        to_ver = semver.VersionInfo.parse(to_version)
        
        # Sort versions between from_version and to_version
        relevant_versions = []
        for version in all_versions:
            ver = semver.VersionInfo.parse(version)
            if to_ver <= ver <= from_ver:
                relevant_versions.append(version)
                
        if not relevant_versions:
            # If no intermediate versions, just use start and end
            return [from_version, to_version]
            
        # Sort by semver in descending order for downgrade
        path = sorted(relevant_versions, key=lambda v: semver.VersionInfo.parse(v), reverse=True)
        
        # Ensure from_version is first and to_version is last
        if path[0] != from_version:
            path.insert(0, from_version)
        if path[-1] != to_version:
            path.append(to_version)
            
        return path
    
    async def delete_version(self, cell_id: str, version: str) -> bool:
        """
        Delete a specific version of a cell.
        
        Args:
            cell_id: Cell identifier
            version: Version to delete
            
        Returns:
            True if deletion was successful, False otherwise
            
        Raises:
            VersionError: If the version cannot be deleted
        """
        if not await self.version_exists(cell_id, version):
            raise VersionError(f"Version {version} does not exist for cell {cell_id}")
            
        try:
            # Get version path
            version_path = self._get_cell_version_path(cell_id, version)
            
            # Delete the version directory
            success = await self.storage_manager.delete_directory(version_path)
            
            if success:
                # Remove from cache
                if cell_id in self.version_cache and version in self.version_cache[cell_id]:
                    del self.version_cache[cell_id][version]
                    
                logger.info(f"Deleted version {version} of cell {cell_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting version {version} of cell {cell_id}: {e}")
            raise VersionError(f"Failed to delete version: {str(e)}")
    
    async def prune_old_versions(self, cell_id: str, keep_count: int = 5) -> List[str]:
        """
        Prune old versions of a cell, keeping only the most recent ones.
        
        Args:
            cell_id: Cell identifier
            keep_count: Number of recent versions to keep
            
        Returns:
            List of deleted version strings
        """
        if keep_count < 1:
            raise ValueError("keep_count must be at least 1")
            
        # Get all versions
        versions = await self.list_versions(cell_id)
        if len(versions) <= keep_count:
            return []  # Nothing to prune
            
        # Sort by semver
        sorted_versions = sorted(versions, key=lambda v: semver.VersionInfo.parse(v), reverse=True)
        
        # Determine versions to delete
        versions_to_keep = sorted_versions[:keep_count]
        versions_to_delete = sorted_versions[keep_count:]
        
        deleted_versions = []
        for version in versions_to_delete:
            try:
                success = await self.delete_version(cell_id, version)
                if success:
                    deleted_versions.append(version)
            except Exception as e:
                logger.warning(f"Failed to delete version {version} of cell {cell_id}: {e}")
        
        return deleted_versions
    
    async def _save_version(
        self, 
        cell_id: str, 
        version: str, 
        cell_data: Dict[str, Any], 
        version_info: VersionInfo
    ) -> None:
        """
        Save a cell version to storage.
        
        Args:
            cell_id: Cell identifier
            version: Version string
            cell_data: Cell data
            version_info: Version information
        """
        # Create version directory
        version_path = self._get_cell_version_path(cell_id, version)
        await self.storage_manager.create_directory(version_path)
        
        # Save cell data
        cell_data_path = os.path.join(version_path, "cell_data.json")
        await self.storage_manager.write_json(cell_data_path, cell_data)
        
        # Save version info
        version_info_path = self._get_version_info_path(cell_id, version)
        await self.storage_manager.write_json(version_info_path, version_info.to_dict())
    
    def _update_cache(self, cell_id: str, version: str, version_info: VersionInfo) -> None:
        """
        Update the version cache.
        
        Args:
            cell_id: Cell identifier
            version: Version string
            version_info: Version information
        """
        if cell_id not in self.version_cache:
            self.version_cache[cell_id] = {}
            
        self.version_cache[cell_id][version] = version_info
        
        # Also update latest if this is the latest version
        versions = list(self.version_cache[cell_id].keys())
        versions = [v for v in versions if v != "latest"]
        
        if versions:
            latest = sorted(versions, key=lambda v: semver.VersionInfo.parse(v), reverse=True)[0]
            if version == latest:
                self.version_cache[cell_id]["latest"] = version_info
    
    def _get_cell_path(self, cell_id: str) -> str:
        """
        Get the storage path for a cell.
        
        Args:
            cell_id: Cell identifier
            
        Returns:
            Path to cell storage
        """
        return os.path.join("cells", cell_id)
    
    def _get_cell_version_path(self, cell_id: str, version: str) -> str:
        """
        Get the storage path for a specific cell version.
        
        Args:
            cell_id: Cell identifier
            version: Version string
            
        Returns:
            Path to cell version storage
        """
        return os.path.join(self._get_cell_path(cell_id), "versions", version)
    
    def _get_version_info_path(self, cell_id: str, version: str) -> str:
        """
        Get the path to version info file.
        
        Args:
            cell_id: Cell identifier
            version: Version string
            
        Returns:
            Path to version info file
        """
        return os.path.join(self._get_cell_version_path(cell_id, version), "version_info.json")
    
    def _generate_content_hash(self, cell_data: Dict[str, Any]) -> str:
        """
        Generate a hash for cell content to verify integrity.
        
        Args:
            cell_data: Cell data
            
        Returns:
            Content hash string
        """
        # Convert to JSON and hash
        content_str = json.dumps(cell_data, sort_keys=True)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    async def invalidate_cache(self, cell_id: Optional[str] = None) -> None:
        """
        Invalidate the version cache.
        
        Args:
            cell_id: Specific cell to invalidate, or None for all
        """
        if cell_id:
            if cell_id in self.version_cache:
                del self.version_cache[cell_id]
        else:
            self.version_cache.clear()


class VersionSpecifier:
    """
    Helper class for parsing and manipulating version specifications.
    """
    
    @staticmethod
    def parse_constraint(constraint: str) -> List[Tuple[str, str]]:
        """
        Parse a version constraint string into operator-version pairs.
        
        Args:
            constraint: Version constraint string (e.g., ">=1.0.0 <2.0.0")
            
        Returns:
            List of (operator, version) tuples
            
        Raises:
            ValueError: If the constraint is invalid
        """
        if not constraint:
            return []
            
        # Split on spaces
        parts = constraint.split()
        
        # Parse each part
        result = []
        operator_pattern = r'^([<>]=?|=|\^|~)(.+)$'
        
        for part in parts:
            # Check if it starts with an operator
            match = re.match(operator_pattern, part)
            
            if match:
                operator, version = match.groups()
                # Validate version
                semver.VersionInfo.parse(version)
                result.append((operator, version))
            else:
                # Assume it's an exact version (=)
                semver.VersionInfo.parse(part)  # Validate
                result.append(("=", part))
        
        return result
    
    @staticmethod
    def constraint_to_range(constraint: str) -> Tuple[Optional[semver.VersionInfo], Optional[semver.VersionInfo]]:
        """
        Convert a constraint to a version range.
        
        Args:
            constraint: Version constraint string
            
        Returns:
            Tuple of (min_version, max_version), either may be None
            
        Raises:
            ValueError: If the constraint is invalid
        """
        if not constraint:
            return (None, None)
            
        parts = VersionSpecifier.parse_constraint(constraint)
        
        min_version = None
        max_version = None
        
        for operator, version in parts:
            ver = semver.VersionInfo.parse(version)
            
            if operator == ">" or operator == ">=":
                if min_version is None or ver > min_version:
                    min_version = ver
            elif operator == "<" or operator == "<=":
                if max_version is None or ver < max_version:
                    max_version = ver
            elif operator == "=" or operator == "==":
                min_version = ver
                max_version = ver
            elif operator == "^":
                # Compatible with: same major version, equal or higher minor/patch
                min_version = ver
                next_major = semver.VersionInfo(major=ver.major + 1, minor=0, patch=0)
                max_version = next_major
            elif operator == "~":
                # Compatible with: same major and minor, equal or higher patch
                min_version = ver
                next_minor = semver.VersionInfo(major=ver.major, minor=ver.minor + 1, patch=0)
                max_version = next_minor
                
        return (min_version, max_version)
    
    @staticmethod
    def is_compatible(version: str, constraint: str) -> bool:
        """
        Check if a version is compatible with a constraint.
        
        Args:
            version: Version string
            constraint: Version constraint string
            
        Returns:
            True if compatible, False otherwise
        """
        try:
            return semver.match(version, constraint)
        except ValueError:
            # If constraint is invalid, try exact match
            return version == constraint

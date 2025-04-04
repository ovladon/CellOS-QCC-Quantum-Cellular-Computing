"""
Cell compatibility checking module for QCC providers.

This module validates that cells adhere to required interfaces and standards,
ensuring they will work correctly with the QCC ecosystem.
"""

import logging
import time
import inspect
import importlib
import pkg_resources
from typing import Dict, List, Any, Set, Optional

from qcc.common.models import Cell
from qcc.common.config import VerificationConfig
from qcc.common.constants import CELL_INTERFACE_VERSION, COMPATIBILITY_MATRIX

from .exceptions import CompatibilityError

logger = logging.getLogger(__name__)

class CompatibilityChecker:
    """
    Checks cell compatibility with the QCC system.
    
    Validates:
    - Cell interface compliance
    - API version compatibility
    - Required method implementations
    - Dependency compatibility
    - Runtime environment compatibility
    """
    
    def __init__(self, config: VerificationConfig):
        """
        Initialize the compatibility checker.
        
        Args:
            config: Verification configuration
        """
        self.config = config
        
        # Load compatibility requirements
        self._load_interface_requirements()
        
        logger.info("Compatibility checker initialized")
    
    async def check(self, cell: Cell) -> Dict[str, Any]:
        """
        Check cell compatibility with the QCC system.
        
        Args:
            cell: The cell to check
            
        Returns:
            Compatibility check result
        """
        start_time = time.time()
        
        # Default result structure
        result = {
            "passed": False,
            "message": "",
            "interface_version": None,
            "issues": [],
            "check_time_ms": 0
        }
        
        try:
            # Check API version compatibility
            api_result = self._check_api_version(cell)
            if not api_result["passed"]:
                result["issues"].append(api_result)
                result["message"] = api_result["message"]
                result["interface_version"] = api_result.get("version")
                result["check_time_ms"] = int((time.time() - start_time) * 1000)
                return result
            
            # Store interface version
            result["interface_version"] = api_result.get("version")
            
            # Perform all compatibility checks
            issues = []
            
            # Check required methods
            method_issues = self._check_required_methods(cell)
            issues.extend(method_issues)
            
            # Check dependencies
            dependency_issues = self._check_dependencies(cell)
            issues.extend(dependency_issues)
            
            # Check capability declarations
            capability_issues = self._check_capabilities(cell)
            issues.extend(capability_issues)
            
            # Store all discovered issues
            result["issues"] = issues
            
            # Determine overall result
            if not issues:
                result["passed"] = True
                result["message"] = "All compatibility checks passed"
            else:
                # Check if any of the issues are critical (non-compatible)
                critical_issues = [issue for issue in issues if issue.get("critical", False)]
                
                if critical_issues:
                    result["passed"] = False
                    result["message"] = f"Critical compatibility issues found: {len(critical_issues)}"
                else:
                    # Non-critical issues (warnings)
                    result["passed"] = True
                    result["message"] = f"Compatible with warnings: {len(issues)} issues found"
            
        except Exception as e:
            result["passed"] = False
            result["message"] = f"Compatibility check error: {str(e)}"
            logger.error("Compatibility check failed for cell %s: %s", 
                        cell.id if hasattr(cell, 'id') else "unknown", str(e))
        
        # Calculate check time
        result["check_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result
    
    def _check_api_version(self, cell: Cell) -> Dict[str, Any]:
        """
        Check cell API version compatibility.
        
        Args:
            cell: The cell to check
            
        Returns:
            API version check result
        """
        # Get cell interface version
        if not hasattr(cell, 'manifest') or not hasattr(cell.manifest, 'interface_version'):
            return {
                "passed": False,
                "critical": True,
                "issue_type": "missing_interface_version",
                "message": "Cell manifest does not specify interface_version",
                "recommendation": f"Add interface_version: {CELL_INTERFACE_VERSION} to manifest"
            }
        
        version = cell.manifest.interface_version
        
        # Check if version is compatible
        if version not in COMPATIBILITY_MATRIX:
            return {
                "passed": False,
                "critical": True,
                "version": version,
                "issue_type": "incompatible_interface_version",
                "message": f"Cell interface version {version} is not compatible",
                "recommendation": f"Update cell to use interface version {CELL_INTERFACE_VERSION}"
            }
        
        compat_info = COMPATIBILITY_MATRIX[version]
        
        if not compat_info["compatible"]:
            return {
                "passed": False,
                "critical": True,
                "version": version,
                "issue_type": "incompatible_interface_version",
                "message": f"Cell interface version {version} is not compatible: {compat_info['reason']}",
                "recommendation": compat_info["recommendation"]
            }
        
        # Version is compatible
        result = {
            "passed": True,
            "version": version,
            "issue_type": None,
            "message": f"Cell interface version {version} is compatible"
        }
        
        # Check if it's not the latest version
        if version != CELL_INTERFACE_VERSION and compat_info.get("deprecated", False):
            result["issue_type"] = "deprecated_interface_version"
            result["message"] = f"Cell uses deprecated interface version {version}"
            result["recommendation"] = f"Consider updating to interface version {CELL_INTERFACE_VERSION}"
            result["critical"] = False
        
        return result
    
    def _check_required_methods(self, cell: Cell) -> List[Dict[str, Any]]:
        """
        Check if cell implements all required methods.
        
        Args:
            cell: The cell to check
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Get interface version to determine required methods
        if not hasattr(cell, 'manifest') or not hasattr(cell.manifest, 'interface_version'):
            # Already reported in _check_api_version
            return issues
        
        version = cell.manifest.interface_version
        
        # Get required methods for this version
        required_methods = self.required_methods.get(version, [])
        
        # Check for required methods
        if hasattr(cell, 'public_methods') and cell.public_methods:
            implemented_methods = set(cell.public_methods)
        elif hasattr(cell, '__dict__'):
            # Try to inspect the object
            implemented_methods = {
                name for name, method in inspect.getmembers(cell, inspect.ismethod)
                if not name.startswith('_')
            }
        else:
            # Can't determine methods, assume missing
            issues.append({
                "passed": False,
                "critical": True,
                "issue_type": "cannot_inspect_methods",
                "message": "Cannot determine cell methods",
                "recommendation": "Ensure cell exposes public_methods attribute or methods can be inspected"
            })
            return issues
        
        # Check each required method
        for method_name in required_methods:
            if method_name not in implemented_methods:
                issues.append({
                    "passed": False,
                    "critical": True,
                    "issue_type": "missing_required_method",
                    "message": f"Cell is missing required method: {method_name}",
                    "recommendation": f"Implement the {method_name} method according to the Cell API specification"
                })
        
        return issues
    
    def _check_dependencies(self, cell: Cell) -> List[Dict[str, Any]]:
        """
        Check cell dependencies for compatibility.
        
        Args:
            cell: The cell to check
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check if cell has dependencies
        if not hasattr(cell, 'dependencies') or not cell.dependencies:
            return issues
        
        # Check each dependency
        for dependency in cell.dependencies:
            # Parse dependency specification
            dep_parts = dependency.split("==") if "==" in dependency else [dependency, ""]
            package_name = dep_parts[0].strip()
            specified_version = dep_parts[1].strip() if len(dep_parts) > 1 else None
            
            # Check if package is not available
            try:
                if specified_version:
                    pkg_resources.require(f"{package_name}=={specified_version}")
                else:
                    pkg_resources.require(package_name)
            except pkg_resources.DistributionNotFound:
                issues.append({
                    "passed": False,
                    "critical": False,  # Not critical as we might be able to install it
                    "issue_type": "missing_dependency",
                    "message": f"Dependency not found: {dependency}",
                    "recommendation": "Install the dependency or provide it with the cell"
                })
                continue
            except pkg_resources.VersionConflict as e:
                issues.append({
                    "passed": False,
                    "critical": True,
                    "issue_type": "dependency_version_conflict",
                    "message": f"Dependency version conflict: {e}",
                    "recommendation": "Adjust dependency version requirements to be compatible with system"
                })
                continue
            
            # Check compatibility with QCC system
            if package_name in self.dependency_compatibility:
                compat_info = self.dependency_compatibility[package_name]
                
                if specified_version:
                    # Check if version is compatible
                    if "compatible_versions" in compat_info:
                        if specified_version not in compat_info["compatible_versions"]:
                            issues.append({
                                "passed": False,
                                "critical": compat_info.get("critical", True),
                                "issue_type": "incompatible_dependency_version",
                                "message": f"Dependency {package_name}=={specified_version} is not compatible with QCC",
                                "recommendation": compat_info.get(
                                    "recommendation", 
                                    f"Use one of the compatible versions: {', '.join(compat_info['compatible_versions'])}"
                                )
                            })
                    
                    if "incompatible_versions" in compat_info and specified_version in compat_info["incompatible_versions"]:
                        issues.append({
                            "passed": False,
                            "critical": compat_info.get("critical", True),
                            "issue_type": "incompatible_dependency_version",
                            "message": f"Dependency {package_name}=={specified_version} is incompatible with QCC: {compat_info.get('reason', '')}",
                            "recommendation": compat_info.get("recommendation", "Update to a compatible version")
                        })
                
                if compat_info.get("deprecated", False):
                    issues.append({
                        "passed": False,
                        "critical": False,  # Warning only
                        "issue_type": "deprecated_dependency",
                        "message": f"Dependency {package_name} is deprecated: {compat_info.get('reason', '')}",
                        "recommendation": compat_info.get("recommendation", "Consider using an alternative package")
                    })
        
        return issues
    
    def _check_capabilities(self, cell: Cell) -> List[Dict[str, Any]]:
        """
        Check cell capability declarations for compatibility.
        
        Args:
            cell: The cell to check
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check if cell has capability declarations
        if not hasattr(cell, 'manifest') or not hasattr(cell.manifest, 'capabilities'):
            issues.append({
                "passed": False,
                "critical": True,
                "issue_type": "missing_capabilities",
                "message": "Cell manifest does not declare capabilities",
                "recommendation": "Add capabilities to the cell manifest"
            })
            return issues
        
        capabilities = cell.manifest.capabilities
        
        if not capabilities:
            issues.append({
                "passed": False,
                "critical": True,
                "issue_type": "no_capabilities",
                "message": "Cell does not declare any capabilities",
                "recommendation": "Declare at least one capability in the cell manifest"
            })
            return issues
        
        # Check each capability
        for capability in capabilities:
            # Check required fields
            required_fields = ["name", "version", "parameters", "outputs"]
            missing_fields = [field for field in required_fields if field not in capability]
            
            if missing_fields:
                issues.append({
                    "passed": False,
                    "critical": True,
                    "issue_type": "incomplete_capability_declaration",
                    "message": f"Capability {capability.get('name', 'unknown')} is missing required fields: {', '.join(missing_fields)}",
                    "recommendation": "Complete the capability declaration with all required fields"
                })
                continue
            
            # Check if capability name is valid
            if not self._is_valid_capability_name(capability["name"]):
                issues.append({
                    "passed": False,
                    "critical": False,
                    "issue_type": "invalid_capability_name",
                    "message": f"Capability name '{capability['name']}' does not follow naming conventions",
                    "recommendation": "Use lowercase letters, numbers, and underscores for capability names"
                })
            
            # Check if capability version is valid
            if not self._is_valid_version(capability["version"]):
                issues.append({
                    "passed": False,
                    "critical": False,
                    "issue_type": "invalid_capability_version",
                    "message": f"Capability {capability['name']} has invalid version format: {capability['version']}",
                    "recommendation": "Use semantic versioning format (e.g., 1.0.0)"
                })
            
            # Check if capability is deprecated
            if capability["name"] in self.deprecated_capabilities:
                issues.append({
                    "passed": False,
                    "critical": False,
                    "issue_type": "deprecated_capability",
                    "message": f"Capability {capability['name']} is deprecated: {self.deprecated_capabilities[capability['name']]['reason']}",
                    "recommendation": self.deprecated_capabilities[capability['name']]["recommendation"]
                })
            
            # Check parameters and outputs format
            if not self._check_capability_parameters(capability["parameters"]):
                issues.append({
                    "passed": False,
                    "critical": False,
                    "issue_type": "invalid_parameters_format",
                    "message": f"Capability {capability['name']} has invalid parameters format",
                    "recommendation": "Ensure each parameter has name, type, and description fields"
                })
            
            if not self._check_capability_outputs(capability["outputs"]):
                issues.append({
                    "passed": False,
                    "critical": False,
                    "issue_type": "invalid_outputs_format",
                    "message": f"Capability {capability['name']} has invalid outputs format",
                    "recommendation": "Ensure each output has name, type, and description fields"
                })
        
        return issues
    
    def _is_valid_capability_name(self, name: str) -> bool:
        """
        Check if a capability name follows naming conventions.
        
        Args:
            name: Capability name to check
            
        Returns:
            True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))
    
    def _is_valid_version(self, version: str) -> bool:
        """
        Check if a version string follows semantic versioning.
        
        Args:
            version: Version string to check
            
        Returns:
            True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?$', version))
    
    def _check_capability_parameters(self, parameters: List[Dict[str, Any]]) -> bool:
        """
        Check if capability parameters are correctly formatted.
        
        Args:
            parameters: List of parameter specifications
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(parameters, list):
            return False
        
        for param in parameters:
            if not isinstance(param, dict):
                return False
            
            # Check for required fields
            if "name" not in param or "type" not in param:
                return False
            
            # Check type validity
            valid_types = ["string", "number", "boolean", "object", "array", "any"]
            if param["type"] not in valid_types:
                return False
        
        return True
    
    def _check_capability_outputs(self, outputs: List[Dict[str, Any]]) -> bool:
        """
        Check if capability outputs are correctly formatted.
        
        Args:
            outputs: List of output specifications
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(outputs, list):
            return False
        
        for output in outputs:
            if not isinstance(output, dict):
                return False
            
            # Check for required fields
            if "name" not in output or "type" not in output:
                return False
            
            # Check type validity
            valid_types = ["string", "number", "boolean", "object", "array", "any"]
            if output["type"] not in valid_types:
                return False
        
        return True
    
    def _load_interface_requirements(self):
        """
        Load interface requirements for different cell interface versions.
        
        In a real implementation, this would be loaded from a configuration
        file or database.
        """
        # Required methods by interface version
        self.required_methods = {
            "1.0.0": [
                "initialize",
                "release"
            ],
            "1.1.0": [
                "initialize",
                "suspend",
                "resume",
                "release"
            ],
            "2.0.0": [
                "initialize",
                "suspend",
                "resume",
                "release",
                "get_capabilities"
            ]
        }
        
        # Dependency compatibility information
        self.dependency_compatibility = {
            "old_package": {
                "deprecated": True,
                "reason": "No longer maintained",
                "recommendation": "Use new_package instead",
                "critical": False
            },
            "conflicting_package": {
                "incompatible_versions": ["1.0.0", "1.1.0"],
                "reason": "Known conflicts with QCC runtime",
                "recommendation": "Use version 1.2.0 or later",
                "critical": True
            },
            "limited_package": {
                "compatible_versions": ["2.0.0", "2.1.0", "2.2.0"],
                "recommendation": "Only versions 2.x are compatible",
                "critical": True
            }
        }
        
        # Deprecated capabilities
        self.deprecated_capabilities = {
            "old_capability": {
                "reason": "Replaced by new_capability",
                "recommendation": "Use new_capability instead"
            },
            "insecure_capability": {
                "reason": "Security vulnerabilities discovered",
                "recommendation": "Use secure_capability which provides the same functionality securely"
            }
        }

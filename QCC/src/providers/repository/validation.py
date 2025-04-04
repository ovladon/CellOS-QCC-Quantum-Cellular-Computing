"""
Cell validation system for Quantum Cellular Computing.

This module provides functionality for validating cells before they
are registered in the repository. It ensures that cells meet the
necessary requirements for structure, security, and compatibility.
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass

from qcc.common.exceptions import ValidationError, SecurityError
from qcc.providers.repository.storage import StorageManager

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """
    Result of a cell validation operation.
    
    Attributes:
        is_valid: Whether the cell passed validation
        errors: List of validation errors
        warnings: List of validation warnings
        info: Additional validation information
    """
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: Dict[str, Any]
    
    def get_report(self) -> Dict[str, Any]:
        """Get a detailed validation report."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }


class CellValidator:
    """
    Validates cells to ensure they meet repository requirements.
    
    This class handles the verification of cell structure, metadata,
    and security aspects before cells are registered in the repository.
    """
    
    def __init__(self, storage_manager: Optional[StorageManager] = None):
        """
        Initialize the cell validator.
        
        Args:
            storage_manager: Optional storage manager for accessing required files
        """
        self.storage_manager = storage_manager
        self.required_manifest_fields = {
            "id", "name", "version", "description", "author", 
            "capabilities", "required_capabilities"
        }
        self.optional_manifest_fields = {
            "license", "documentation", "dependencies", "compatibility",
            "tags", "metadata", "security_profile", "resource_requirements"
        }
    
    async def validate_cell(self, cell_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a cell before registration.
        
        Args:
            cell_data: Cell data including manifest and code
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        info = {}
        
        # Validate basic structure
        structure_errors = self._validate_structure(cell_data)
        errors.extend(structure_errors)
        
        if structure_errors:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                info=info
            )
        
        # Validate manifest
        manifest_errors, manifest_warnings, manifest_info = self._validate_manifest(cell_data.get("manifest", {}))
        errors.extend(manifest_errors)
        warnings.extend(manifest_warnings)
        info.update(manifest_info)
        
        # Validate code
        code_errors, code_warnings, code_info = await self._validate_code(
            cell_data.get("code", {}),
            cell_data.get("manifest", {})
        )
        errors.extend(code_errors)
        warnings.extend(code_warnings)
        info.update(code_info)
        
        # Validate security aspects
        security_errors, security_warnings = await self._validate_security(cell_data)
        errors.extend(security_errors)
        warnings.extend(security_warnings)
        
        # Additional validations for the cell's specific type
        cell_type = cell_data.get("manifest", {}).get("type", "general")
        if cell_type == "system":
            type_errors, type_warnings = self._validate_system_cell(cell_data)
            errors.extend(type_errors)
            warnings.extend(type_warnings)
        elif cell_type == "middleware":
            type_errors, type_warnings = self._validate_middleware_cell(cell_data)
            errors.extend(type_errors)
            warnings.extend(type_warnings)
        elif cell_type == "application":
            type_errors, type_warnings = self._validate_application_cell(cell_data)
            errors.extend(type_errors)
            warnings.extend(type_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _validate_structure(self, cell_data: Dict[str, Any]) -> List[str]:
        """
        Validate the basic structure of a cell.
        
        Args:
            cell_data: Cell data
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for empty data
        if not cell_data:
            errors.append("Cell data is empty")
            return errors
        
        # Check for required top-level fields
        if "manifest" not in cell_data:
            errors.append("Cell is missing manifest")
        
        if "code" not in cell_data:
            errors.append("Cell is missing code")
        
        # Check manifest structure if present
        if "manifest" in cell_data and not isinstance(cell_data["manifest"], dict):
            errors.append("Manifest must be a dictionary")
        
        # Check code structure if present
        if "code" in cell_data:
            if not isinstance(cell_data["code"], dict):
                errors.append("Code must be a dictionary")
            else:
                # Check for implementation based on format
                code_format = cell_data.get("manifest", {}).get("code_format", "python")
                
                if code_format == "python":
                    if "source" not in cell_data["code"]:
                        errors.append("Python code must include 'source' field")
                elif code_format == "wasm":
                    if "binary" not in cell_data["code"]:
                        errors.append("WebAssembly code must include 'binary' field")
                elif code_format == "javascript":
                    if "source" not in cell_data["code"]:
                        errors.append("JavaScript code must include 'source' field")
        
        return errors
    
    def _validate_manifest(self, manifest: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """
        Validate the cell manifest.
        
        Args:
            manifest: Cell manifest
            
        Returns:
            Tuple of (errors, warnings, info)
        """
        errors = []
        warnings = []
        info = {"manifest_fields": {}}
        
        # Check for empty manifest
        if not manifest:
            errors.append("Manifest is empty")
            return errors, warnings, info
        
        # Check for required fields
        for field in self.required_manifest_fields:
            if field not in manifest:
                errors.append(f"Manifest is missing required field: {field}")
            else:
                info["manifest_fields"][field] = True
        
        # Track optional fields
        for field in self.optional_manifest_fields:
            info["manifest_fields"][field] = field in manifest
        
        # Check id format
        if "id" in manifest:
            if not isinstance(manifest["id"], str):
                errors.append("Manifest 'id' must be a string")
            elif not re.match(r'^[a-z0-9_-]+$', manifest["id"]):
                errors.append("Manifest 'id' must contain only lowercase letters, numbers, underscores, and hyphens")
        
        # Check version format
        if "version" in manifest:
            if not isinstance(manifest["version"], str):
                errors.append("Manifest 'version' must be a string")
            elif not re.match(r'^\d+\.\d+\.\d+$', manifest["version"]):
                errors.append("Manifest 'version' must follow semantic versioning (e.g., 1.0.0)")
        
        # Check capabilities format
        if "capabilities" in manifest:
            if not isinstance(manifest["capabilities"], dict):
                errors.append("Manifest 'capabilities' must be a dictionary")
            else:
                # Validate each capability
                for cap_name, cap_info in manifest["capabilities"].items():
                    if not isinstance(cap_info, dict):
                        errors.append(f"Capability '{cap_name}' info must be a dictionary")
                    elif "version" not in cap_info:
                        errors.append(f"Capability '{cap_name}' is missing version")
        
        # Check required_capabilities format
        if "required_capabilities" in manifest:
            if not isinstance(manifest["required_capabilities"], list):
                errors.append("Manifest 'required_capabilities' must be a list")
            
        # Check dependencies format
        if "dependencies" in manifest:
            if not isinstance(manifest["dependencies"], dict):
                errors.append("Manifest 'dependencies' must be a dictionary")
            else:
                # Validate each dependency
                for dep_id, dep_constraint in manifest["dependencies"].items():
                    if not isinstance(dep_constraint, str):
                        errors.append(f"Dependency constraint for '{dep_id}' must be a string")
        
        # Check resource_requirements format
        if "resource_requirements" in manifest:
            if not isinstance(manifest["resource_requirements"], dict):
                errors.append("Manifest 'resource_requirements' must be a dictionary")
            else:
                for req_name in ["memory_mb", "cpu_percent", "storage_mb"]:
                    if req_name in manifest["resource_requirements"]:
                        value = manifest["resource_requirements"][req_name]
                        if not isinstance(value, (int, float)) or value < 0:
                            errors.append(f"Resource requirement '{req_name}' must be a non-negative number")
        
        # Warn about excessively large resource requirements
        if "resource_requirements" in manifest:
            reqs = manifest["resource_requirements"]
            if "memory_mb" in reqs and reqs["memory_mb"] > 500:
                warnings.append(f"High memory requirement: {reqs['memory_mb']} MB")
            if "cpu_percent" in reqs and reqs["cpu_percent"] > 50:
                warnings.append(f"High CPU requirement: {reqs['cpu_percent']}%")
            if "storage_mb" in reqs and reqs["storage_mb"] > 1000:
                warnings.append(f"High storage requirement: {reqs['storage_mb']} MB")
        
        # Check for recommended fields
        if "license" not in manifest:
            warnings.append("No license specified in manifest")
        
        if "documentation" not in manifest:
            warnings.append("No documentation provided in manifest")
        
        return errors, warnings, info
    
    async def _validate_code(
        self, 
        code: Dict[str, Any], 
        manifest: Dict[str, Any]
    ) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """
        Validate the cell code.
        
        Args:
            code: Cell code
            manifest: Cell manifest
            
        Returns:
            Tuple of (errors, warnings, info)
        """
        errors = []
        warnings = []
        info = {"code_metrics": {}}
        
        # Check for empty code
        if not code:
            errors.append("Code is empty")
            return errors, warnings, info
        
        # Get code format
        code_format = manifest.get("code_format", "python")
        
        # Validate based on format
        if code_format == "python":
            return await self._validate_python_code(code, manifest)
        elif code_format == "wasm":
            return await self._validate_wasm_code(code, manifest)
        elif code_format == "javascript":
            return await self._validate_javascript_code(code, manifest)
        else:
            errors.append(f"Unsupported code format: {code_format}")
            return errors, warnings, info
    
    async def _validate_python_code(
        self, 
        code: Dict[str, Any], 
        manifest: Dict[str, Any]
    ) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """
        Validate Python cell code.
        
        Args:
            code: Cell code
            manifest: Cell manifest
            
        Returns:
            Tuple of (errors, warnings, info)
        """
        errors = []
        warnings = []
        info = {"code_metrics": {}}
        
        # Check for source code
        if "source" not in code:
            errors.append("Python code must include 'source' field")
            return errors, warnings, info
        
        source = code["source"]
        if not isinstance(source, str):
            errors.append("Source code must be a string")
            return errors, warnings, info
        
        # Measure code size
        code_size = len(source.encode('utf-8'))
        info["code_metrics"]["size_bytes"] = code_size
        
        if code_size > 1024 * 1024:  # 1 MB
            warnings.append(f"Code size is large: {code_size / 1024 / 1024:.2f} MB")
        
        # Count lines of code
        lines = source.split('\n')
        info["code_metrics"]["lines"] = len(lines)
        
        # Perform basic syntax check
        try:
            compile(source, '<string>', 'exec')
        except SyntaxError as e:
            errors.append(f"Python syntax error: {str(e)}")
        
        # Check for required imports based on capabilities
        capabilities = manifest.get("capabilities", {})
        for cap_name in capabilities:
            if cap_name not in source:
                warnings.append(f"Capability '{cap_name}' is declared but not found in code")
        
        # Check for presence of BaseCell class inheritance
        if "BaseCell" not in source or "class" not in source:
            warnings.append("Cell does not appear to inherit from BaseCell")
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            (r'os\.system\(', "Uses os.system() which can execute arbitrary commands"),
            (r'subprocess\.', "Uses subprocess module which can execute arbitrary commands"),
            (r'eval\(', "Uses eval() which can execute arbitrary code"),
            (r'exec\(', "Uses exec() which can execute arbitrary code"),
            (r'__import__\(', "Uses __import__() which can import potentially unsafe modules"),
            (r'open\(.*,.*[\'"]w[\'"]\)', "Writes to filesystem which might not be permitted")
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, source):
                warnings.append(f"Security concern: {message}")
        
        # Check for imports of common stdlib modules
        common_modules = [
            "sys", "os", "shutil", "subprocess", "socket", "threading",
            "multiprocessing", "concurrent", "urllib", "http", "ftplib",
            "telnetlib", "smtplib", "poplib", "imaplib"
        ]
        
        for module in common_modules:
            pattern = fr'import\s+{module}|from\s+{module}\s+import'
            if re.search(pattern, source):
                info.setdefault("imported_modules", []).append(module)
        
        return errors, warnings, info
    
    async def _validate_wasm_code(
        self, 
        code: Dict[str, Any], 
        manifest: Dict[str, Any]
    ) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """
        Validate WebAssembly cell code.
        
        Args:
            code: Cell code
            manifest: Cell manifest
            
        Returns:
            Tuple of (errors, warnings, info)
        """
        errors = []
        warnings = []
        info = {"code_metrics": {}}
        
        # Check for binary data
        if "binary" not in code:
            errors.append("WebAssembly code must include 'binary' field")
            return errors, warnings, info
        
        binary = code["binary"]
        if not isinstance(binary, str):
            errors.append("WebAssembly binary must be a base64-encoded string")
            return errors, warnings, info
        
        # Decode base64 to check for valid format
        try:
            import base64
            binary_data = base64.b64decode(binary)
            
            # Check for WASM magic number
            if not binary_data.startswith(b'\x00\x61\x73\x6D'):
                errors.append("WebAssembly binary does not have valid magic number")
            
            # Measure code size
            code_size = len(binary_data)
            info["code_metrics"]["size_bytes"] = code_size
            
            if code_size > 10 * 1024 * 1024:  # 10 MB
                warnings.append(f"WebAssembly binary is large: {code_size / 1024 / 1024:.2f} MB")
            
        except Exception as e:
            errors.append(f"Failed to decode WebAssembly binary: {str(e)}")
        
        # Check for required exports based on capabilities
        exports = code.get("exports", [])
        capabilities = manifest.get("capabilities", {})
        
        if not exports:
            warnings.append("No exports declared for WebAssembly module")
        else:
            for cap_name in capabilities:
                if not any(export.get("name") == cap_name for export in exports):
                    warnings.append(f"Capability '{cap_name}' is declared but not found in exports")
        
        return errors, warnings, info
    
    async def _validate_javascript_code(
        self, 
        code: Dict[str, Any], 
        manifest: Dict[str, Any]
    ) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """
        Validate JavaScript cell code.
        
        Args:
            code: Cell code
            manifest: Cell manifest
            
        Returns:
            Tuple of (errors, warnings, info)
        """
        errors = []
        warnings = []
        info = {"code_metrics": {}}
        
        # Check for source code
        if "source" not in code:
            errors.append("JavaScript code must include 'source' field")
            return errors, warnings, info
        
        source = code["source"]
        if not isinstance(source, str):
            errors.append("Source code must be a string")
            return errors, warnings, info
        
        # Measure code size
        code_size = len(source.encode('utf-8'))
        info["code_metrics"]["size_bytes"] = code_size
        
        if code_size > 1024 * 1024:  # 1 MB
            warnings.append(f"Code size is large: {code_size / 1024 / 1024:.2f} MB")
        
        # Count lines of code
        lines = source.split('\n')
        info["code_metrics"]["lines"] = len(lines)
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            (r'eval\(', "Uses eval() which can execute arbitrary code"),
            (r'new Function\(', "Uses Function constructor which can execute arbitrary code"),
            (r'document\.write\(', "Uses document.write() which can modify page content"),
            (r'localStorage', "Uses localStorage which might not be available"),
            (r'sessionStorage', "Uses sessionStorage which might not be available")
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, source):
                warnings.append(f"Security concern: {message}")
        
        # Check for required functions based on capabilities
        capabilities = manifest.get("capabilities", {})
        for cap_name in capabilities:
            function_pattern = fr'function\s+{cap_name}\s*\('
            method_pattern = fr'[a-zA-Z0-9_]+\.prototype\.{cap_name}\s*='
            if not (re.search(function_pattern, source) or re.search(method_pattern, source)):
                warnings.append(f"Capability '{cap_name}' is declared but not found in code")
        
        return errors, warnings, info
    
    async def _validate_security(self, cell_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Validate security aspects of a cell.
        
        Args:
            cell_data: Cell data
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        manifest = cell_data.get("manifest", {})
        
        # Check for required security fields
        if "security_profile" not in manifest:
            warnings.append("No security profile specified in manifest")
        else:
            security_profile = manifest["security_profile"]
            
            # Check for required security fields
            if "permissions" not in security_profile:
                warnings.append("No permissions specified in security profile")
            
            # Validate permissions
            if "permissions" in security_profile:
                permissions = security_profile["permissions"]
                
                if not isinstance(permissions, list):
                    errors.append("Permissions must be a list")
                else:
                    # Check for suspicious permissions
                    suspicious_permissions = [
                        "system_exec", "file_write", "network_all",
                        "process_create", "env_modify", "sudo"
                    ]
                    
                    for perm in suspicious_permissions:
                        if perm in permissions:
                            warnings.append(f"Cell requests sensitive permission: {perm}")
        
        # Check for secure execution environment requirements
        if "execution_environment" in manifest:
            env = manifest["execution_environment"]
            
            if "isolation_level" in env and env["isolation_level"] == "none":
                warnings.append("Cell requests no isolation which is a security risk")
            
            if "privileged" in env and env["privileged"]:
                warnings.append("Cell requests privileged execution which is a security risk")
        
        # Check for secure resource limits
        if "resource_requirements" in manifest:
            reqs = manifest["resource_requirements"]
            
            if "unlimited" in reqs and reqs["unlimited"]:
                warnings.append("Cell requests unlimited resources which is a security risk")
        
        # Cell type-specific security checks
        cell_type = manifest.get("type", "general")
        
        if cell_type == "system":
            # System cells should have explicit security documentation
            if "security_documentation" not in manifest:
                warnings.append("System cell should have explicit security documentation")
                
            # System cells with network access are high risk
            if manifest.get("security_profile", {}).get("permissions", []) and "network" in manifest["security_profile"]["permissions"]:
                warnings.append("System cell with network access is high risk")
        
        return errors, warnings
    
    def _validate_system_cell(self, cell_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Validate a system cell.
        
        Args:
            cell_data: Cell data
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        manifest = cell_data.get("manifest", {})
        
        # System cells must have detailed documentation
        if "documentation" not in manifest or not manifest["documentation"]:
            errors.append("System cell must have detailed documentation")
        
        # System cells should specify resource requirements
        if "resource_requirements" not in manifest:
            warnings.append("System cell should specify resource requirements")
        
        # System cells should specify security profile
        if "security_profile" not in manifest:
            errors.append("System cell must specify security profile")
        
        return errors, warnings
    
    def _validate_middleware_cell(self, cell_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Validate a middleware cell.
        
        Args:
            cell_data: Cell data
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        manifest = cell_data.get("manifest", {})
        
        # Middleware cells must specify their integrations
        if "integrations" not in manifest:
            errors.append("Middleware cell must specify integrations")
        
        # Middleware cells should have compatibility information
        if "compatibility" not in manifest:
            warnings.append("Middleware cell should specify compatibility information")
        
        return errors, warnings
    
    def _validate_application_cell(self, cell_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Validate an application cell.
        
        Args:
            cell_data: Cell data
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        manifest = cell_data.get("manifest", {})
        
        # Application cells should have user-friendly documentation
        if "user_documentation" not in manifest:
            warnings.append("Application cell should have user-friendly documentation")
        
        # Application cells should have screenshots or UI description
        if "ui" not in manifest:
            warnings.append("Application cell should describe its user interface")
        
        return errors, warnings

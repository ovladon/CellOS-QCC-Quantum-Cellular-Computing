"""
Permission validation module for cell verification.

This module ensures that cells only request permissions they legitimately need
and that those permissions are appropriately scoped for their functionality.
"""

import logging
import time
from typing import Dict, List, Any, Set, Optional

from qcc.common.models import Cell
from qcc.common.config import VerificationConfig

from .exceptions import PermissionError

logger = logging.getLogger(__name__)

class PermissionValidator:
    """
    Validates cell permission requests against security policies.
    
    Ensures that cells:
    - Only request permissions they need
    - Use the principle of least privilege
    - Do not request dangerous permission combinations
    - Provide proper justification for sensitive permissions
    """
    
    def __init__(self, config: VerificationConfig):
        """
        Initialize the permission validator.
        
        Args:
            config: Verification configuration
        """
        self.config = config
        
        # Load permission policies
        self._load_permission_policies()
        
        logger.info("Permission validator initialized with verification level: %s", 
                   self.config.verification_level)
    
    async def validate(self, cell: Cell) -> Dict[str, Any]:
        """
        Validate cell permission requests.
        
        Args:
            cell: The cell to validate
            
        Returns:
            Validation result
        """
        start_time = time.time()
        
        # Default result structure
        result = {
            "passed": False,
            "message": "",
            "issues": [],
            "validation_time_ms": 0
        }
        
        try:
            # Extract requested permissions
            permissions = self._extract_requested_permissions(cell)
            
            # If no permissions requested, this is acceptable
            if not permissions:
                result["passed"] = True
                result["message"] = "No permissions requested"
                result["validation_time_ms"] = int((time.time() - start_time) * 1000)
                return result
            
            # Check each permission
            issues = []
            
            # Check for blocked permissions
            blocked_issues = self._check_blocked_permissions(permissions)
            issues.extend(blocked_issues)
            
            # Check for permission/capability mismatches
            mismatch_issues = self._check_permission_capability_mismatch(cell, permissions)
            issues.extend(mismatch_issues)
            
            # Check for dangerous permission combinations
            combination_issues = self._check_dangerous_combinations(permissions)
            issues.extend(combination_issues)
            
            # Check permission scopes
            scope_issues = self._check_permission_scopes(cell, permissions)
            issues.extend(scope_issues)
            
            # Check permission justifications
            if self.config.require_permission_justification:
                justification_issues = self._check_permission_justifications(cell, permissions)
                issues.extend(justification_issues)
            
            # Store discovered issues
            result["issues"] = issues
            
            # Determine overall result
            if not issues:
                result["passed"] = True
                result["message"] = "All permission checks passed"
            else:
                # Check if any of the issues are critical (blocking)
                critical_issues = [issue for issue in issues if issue.get("critical", False)]
                
                if critical_issues:
                    result["passed"] = False
                    result["message"] = f"Critical permission issues found: {len(critical_issues)}"
                else:
                    # Non-critical issues (warnings)
                    result["passed"] = True
                    result["message"] = f"Permissions valid with warnings: {len(issues)} issues found"
            
        except Exception as e:
            result["passed"] = False
            result["message"] = f"Permission validation error: {str(e)}"
            logger.error("Permission validation failed for cell %s: %s", 
                        cell.id if hasattr(cell, 'id') else "unknown", str(e))
        
        # Calculate validation time
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result
    
    def _extract_requested_permissions(self, cell: Cell) -> Dict[str, Any]:
        """
        Extract permission requests from a cell.
        
        Args:
            cell: The cell to extract permissions from
            
        Returns:
            Dictionary of permission requests
        """
        if not hasattr(cell, 'manifest'):
            return {}
        
        manifest = cell.manifest
        
        # Check if manifest has permissions section
        if not hasattr(manifest, 'permissions'):
            return {}
        
        return manifest.permissions
    
    def _check_blocked_permissions(self, permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for permissions that are completely blocked.
        
        Args:
            permissions: Requested permissions
            
        Returns:
            List of permission issues
        """
        issues = []
        
        for perm_name, perm_spec in permissions.items():
            if perm_name in self.blocked_permissions:
                block_info = self.blocked_permissions[perm_name]
                
                issues.append({
                    "critical": True,
                    "issue_type": "blocked_permission",
                    "permission": perm_name,
                    "message": f"Permission '{perm_name}' is blocked: {block_info['reason']}",
                    "recommendation": block_info.get("recommendation", "Remove this permission request")
                })
        
        return issues
    
    def _check_permission_capability_mismatch(self, 
                                            cell: Cell, 
                                            permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if requested permissions match declared capabilities.
        
        Args:
            cell: The cell being validated
            permissions: Requested permissions
            
        Returns:
            List of permission issues
        """
        issues = []
        
        # Skip if cell doesn't have capability declarations
        if not hasattr(cell, 'manifest') or not hasattr(cell.manifest, 'capabilities'):
            return issues
        
        capabilities = cell.manifest.capabilities
        
        # Get declared capability names
        capability_names = [cap.get("name") for cap in capabilities if "name" in cap]
        
        # Check if permissions align with capabilities
        for perm_name, perm_spec in permissions.items():
            # Get the capabilities this permission is typically needed for
            typical_capabilities = self.permission_capability_map.get(perm_name, [])
            
            # If this permission is typically used by specific capabilities
            # check if the cell declares any of those capabilities
            if typical_capabilities:
                matches = [cap for cap in capability_names if cap in typical_capabilities]
                
                if not matches:
                    issues.append({
                        "critical": False,  # Warning only
                        "issue_type": "permission_capability_mismatch",
                        "permission": perm_name,
                        "message": f"Permission '{perm_name}' is typically used by capabilities {typical_capabilities}, but none are declared",
                        "recommendation": "Either add a relevant capability or remove this permission"
                    })
        
        return issues
    
    def _check_dangerous_combinations(self, permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for dangerous combinations of permissions.
        
        Args:
            permissions: Requested permissions
            
        Returns:
            List of permission issues
        """
        issues = []
        
        requested_perms = set(permissions.keys())
        
        for combo, combo_info in self.dangerous_combinations.items():
            combo_perms = set(combo)
            
            if combo_perms.issubset(requested_perms):
                issues.append({
                    "critical": combo_info.get("critical", False),
                    "issue_type": "dangerous_permission_combination",
                    "permissions": list(combo),
                    "message": f"Dangerous permission combination: {', '.join(combo)} - {combo_info['reason']}",
                    "recommendation": combo_info.get("recommendation", "Avoid using these permissions together")
                })
        
        return issues
    
    def _check_permission_scopes(self, 
                               cell: Cell, 
                               permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if permission scopes are appropriate.
        
        Args:
            cell: The cell being validated
            permissions: Requested permissions
            
        Returns:
            List of permission issues
        """
        issues = []
        
        for perm_name, perm_spec in permissions.items():
            # Skip if permission doesn't exist in our map
            if perm_name not in self.permission_scopes:
                continue
            
            # Get the scope info
            scope_info = self.permission_scopes[perm_name]
            
            # Check if permission has scope field
            if not isinstance(perm_spec, dict) or "scope" not in perm_spec:
                if scope_info.get("scope_required", False):
                    issues.append({
                        "critical": True,
                        "issue_type": "missing_permission_scope",
                        "permission": perm_name,
                        "message": f"Permission '{perm_name}' requires a scope specification",
                        "recommendation": "Add a 'scope' field to the permission specification"
                    })
                continue
            
            scope = perm_spec["scope"]
            
            # Check scope format
            if "format" in scope_info:
                import re
                pattern = scope_info["format"]
                
                # If scope is a list, check each item
                if isinstance(scope, list):
                    invalid_items = [item for item in scope if not re.match(pattern, str(item))]
                    
                    if invalid_items:
                        issues.append({
                            "critical": True,
                            "issue_type": "invalid_permission_scope_format",
                            "permission": perm_name,
                            "message": f"Invalid scope format for permission '{perm_name}': {invalid_items}",
                            "recommendation": f"Ensure all scope items match the required format: {pattern}"
                        })
                elif not re.match(pattern, str(scope)):
                    issues.append({
                        "critical": True,
                        "issue_type": "invalid_permission_scope_format",
                        "permission": perm_name,
                        "message": f"Invalid scope format for permission '{perm_name}': {scope}",
                        "recommendation": f"Ensure scope matches the required format: {pattern}"
                    })
            
            # Check if too broad
            if "too_broad_indicators" in scope_info:
                indicators = scope_info["too_broad_indicators"]
                
                # Check if scope is a list
                if isinstance(scope, list):
                    for indicator in indicators:
                        if indicator in scope:
                            issues.append({
                                "critical": False,  # Warning only
                                "issue_type": "overly_broad_permission_scope",
                                "permission": perm_name,
                                "message": f"Overly broad scope for permission '{perm_name}': {indicator}",
                                "recommendation": "Restrict the permission scope to only what is necessary"
                            })
                elif isinstance(scope, str) and scope in indicators:
                    issues.append({
                        "critical": False,  # Warning only
                        "issue_type": "overly_broad_permission_scope",
                        "permission": perm_name,
                        "message": f"Overly broad scope for permission '{perm_name}': {scope}",
                        "recommendation": "Restrict the permission scope to only what is necessary"
                    })
        
        return issues
    
    def _check_permission_justifications(self, 
                                      cell: Cell, 
                                      permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if sensitive permissions have proper justifications.
        
        Args:
            cell: The cell being validated
            permissions: Requested permissions
            
        Returns:
            List of permission issues
        """
        issues = []
        
        for perm_name, perm_spec in permissions.items():
            # Check if permission is in the sensitive list
            if perm_name in self.sensitive_permissions:
                # Check if permission spec has justification
                if not isinstance(perm_spec, dict) or "justification" not in perm_spec:
                    issues.append({
                        "critical": self.config.verification_level == "maximum",
                        "issue_type": "missing_permission_justification",
                        "permission": perm_name,
                        "message": f"Sensitive permission '{perm_name}' is missing justification",
                        "recommendation": "Add a 'justification' field explaining why this permission is needed"
                    })
                elif len(str(perm_spec["justification"])) < 20:
                    # Justification is too short/vague
                    issues.append({
                        "critical": False,  # Warning only
                        "issue_type": "insufficient_permission_justification",
                        "permission": perm_name,
                        "message": f"Justification for permission '{perm_name}' is too brief",
                        "recommendation": "Provide a more detailed justification"
                    })
        
        return issues
    
    def _load_permission_policies(self):
        """
        Load permission policies and constraints.
        
        In a real implementation, these would be loaded from a configuration
        file or database.
        """
        # Permissions that are completely blocked (not allowed)
        self.blocked_permissions = {
            "system_kernel_access": {
                "reason": "Direct kernel access is not allowed for security",
                "recommendation": "Use higher-level system APIs instead"
            },
            "network_raw_socket": {
                "reason": "Raw socket access creates security vulnerabilities",
                "recommendation": "Use higher-level network APIs instead"
            },
            "user_credential_access": {
                "reason": "Direct access to user credentials is prohibited",
                "recommendation": "Use the authentication cell for credential operations"
            }
        }
        
        # Mapping of permissions to the capabilities they're typically used with
        self.permission_capability_map = {
            "file_system_read": ["file_system", "document_processing", "media_player"],
            "file_system_write": ["file_system", "document_processing", "media_editor"],
            "network_outbound": ["http_client", "api_client", "web_browser"],
            "network_inbound": ["http_server", "api_server", "network_utility"],
            "user_data_access": ["user_profile", "personalization", "data_analysis"],
            "notification_send": ["notification_manager", "reminder", "calendar"],
            "location_access": ["map", "navigation", "geolocation"],
            "camera_access": ["camera", "video_chat", "image_processing"],
            "microphone_access": ["voice_recognition", "audio_recording", "voice_chat"]
        }
        
        # Dangerous combinations of permissions
        self.dangerous_combinations = {
            ("file_system_write", "network_outbound"): {
                "reason": "Could potentially be used for data exfiltration",
                "recommendation": "If both permissions are necessary, add strict scoping and monitoring",
                "critical": False
            },
            ("system_execute", "network_outbound"): {
                "reason": "High risk of being used for malicious purposes",
                "recommendation": "This combination requires extraordinary justification and extreme scoping",
                "critical": True
            },
            ("user_data_access", "network_outbound", "file_system_write"): {
                "reason": "Combination enables data harvesting and exfiltration",
                "recommendation": "Separate these permissions across different cells with clear boundaries",
                "critical": True
            }
        }

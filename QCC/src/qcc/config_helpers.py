"""
Helper functions for working with QCC configuration files.
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional

def resolve_extends(config_path: str) -> Dict[str, Any]:
    """
    Load a configuration file and resolve any 'extends' references.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Resolved configuration dictionary
    """
    path = Path(config_path)
    
    # Read the file
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    
    # Check for extends directive
    if "extends" in config:
        # Get the base configuration path
        base_path = path.parent / config["extends"]
        
        # Load the base configuration
        base_config = resolve_extends(str(base_path))
        
        # Remove extends directive to avoid circular references
        del config["extends"]
        
        # Merge configurations
        merged_config = deep_merge(base_config, config)
        return merged_config
    
    return config

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries, with override values taking precedence.
    
    Args:
        base: Base dictionary
        override: Dictionary with override values
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override or add value
            result[key] = value
    
    return result

def expand_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively expand environment variables in configuration values.
    
    Supports the syntax ${ENV_VAR} or $ENV_VAR in string values.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with environment variables expanded
    """
    result = {}
    
    for key, value in config.items():
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = expand_env_vars(value)
        elif isinstance(value, list):
            # Process list items
            result[key] = [
                expand_env_vars({0: item})[0]
                if isinstance(item, (dict, str))
                else item
                for item in value
            ]
        elif isinstance(value, str):
            # Expand environment variables in strings
            # Match ${VAR} style
            pattern1 = r'\${([A-Za-z0-9_]+)}'
            # Match $VAR style
            pattern2 = r'\$([A-Za-z0-9_]+)'
            
            # First replace ${VAR} style
            value = re.sub(pattern1, lambda m: os.environ.get(m.group(1), m.group(0)), value)
            # Then replace $VAR style
            value = re.sub(pattern2, lambda m: os.environ.get(m.group(1), m.group(0)), value)
            
            result[key] = value
        else:
            # Keep other values as is
            result[key] = value
    
    return result

def load_config_with_env(config_path: str) -> Dict[str, Any]:
    """
    Load a configuration file, resolve 'extends', and expand environment variables.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Processed configuration dictionary
    """
    # Resolve extends
    config = resolve_extends(config_path)
    
    # Expand environment variables
    config = expand_env_vars(config)
    
    return config

def get_cell_config(config: Dict[str, Any], cell_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific cell.
    
    Args:
        config: Main configuration dictionary
        cell_name: Name of the cell
        
    Returns:
        Cell-specific configuration
    """
    # Try to load from cell_config.yaml
    cell_config_path = Path("config/cell_config.yaml")
    
    if cell_config_path.exists():
        with open(cell_config_path, "r") as f:
            cell_configs = yaml.safe_load(f)
            
        if cell_name in cell_configs:
            return cell_configs[cell_name]
    
    # Return empty config if not found
    return {}

"""
Configuration utilities for the QCC framework.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If configuration format is invalid
    """
    path = Path(config_path)
    
    # Check if file exists
    if not path.exists():
        # Look for the file in standard locations
        potential_paths = [
            Path("config") / path.name,
            Path("config") / "development.yaml",
            Path("config") / "config.yaml",
            Path(os.path.expanduser("~")) / ".qcc" / path.name
        ]
        
        for p in potential_paths:
            if p.exists():
                path = p
                break
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load the file
    with open(path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
    
    # Check if config is a dictionary
    if not isinstance(config, dict):
        raise ValueError("Configuration file must contain a YAML dictionary")
    
    # Add default values for required sections
    _ensure_defaults(config)
    
    return config

def _ensure_defaults(config: Dict[str, Any]) -> None:
    """Add default values for required configuration sections."""
    # Assembler defaults
    config.setdefault("assembler", {})
    config["assembler"].setdefault("user_id", "anonymous")
    config["assembler"].setdefault("max_solutions", 10)
    
    # Provider defaults
    config.setdefault("providers", {})
    config["providers"].setdefault("urls", ["http://localhost:8081"])
    config["providers"].setdefault("cache_dir", "data/cell-cache")
    
    # Quantum trail defaults
    config.setdefault("quantum_trail", {})
    config["quantum_trail"].setdefault("blockchain_path", "data/quantum-trail")
    config["quantum_trail"].setdefault("encryption_key", "development-key-only")
    
    # Server defaults
    config.setdefault("server", {})
    config["server"].setdefault("host", "127.0.0.1")
    config["server"].setdefault("port", 8080)
    config["server"].setdefault("reload", False)
    
    # Cell defaults
    config.setdefault("cells", {})
    config["cells"].setdefault("directory", "cells")

def get_config_value(config: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get a value from the configuration using a dot-separated path.
    
    Args:
        config: Configuration dictionary
        path: Dot-separated path to the value (e.g., "assembler.user_id")
        default: Default value if path is not found
        
    Returns:
        Configuration value or default
    """
    parts = path.split(".")
    current = config
    
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    
    return current

"""
Data models for intent interpretation in the QCC Assembler.

This module defines the data structures used for representing
interpreted user intent and capability requirements.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class RequiredCapability:
    """
    Represents a capability required by the user's intent.
    
    Attributes:
        name (str): Name of the capability
        parameters (Dict[str, Any]): Parameters for configuring the capability
        priority (int): Priority level (lower numbers are higher priority)
        confidence (float): Confidence score for this capability requirement (0-1)
    """
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class IntentAnalysis:
    """
    Represents the complete analysis of a user's intent.
    
    Attributes:
        original_request (str): The original user request text
        normalized_request (str): Normalized version of the request
        required_capabilities (List[RequiredCapability]): Required capabilities
        suggested_connections (Dict[str, List[str]]): Suggested cell connections
        analyzed_at (str): ISO timestamp of when the analysis was performed
        context_used (bool): Whether context information was used
        confidence_score (float): Overall confidence in the analysis (0-1)
    """
    original_request: str
    normalized_request: str
    required_capabilities: List[RequiredCapability] = field(default_factory=list)
    suggested_connections: Dict[str, List[str]] = field(default_factory=dict)
    analyzed_at: str = ""
    context_used: bool = False
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        # Convert capability objects to dictionaries
        result["required_capabilities"] = [
            cap.to_dict() for cap in self.required_capabilities
        ]
        return result

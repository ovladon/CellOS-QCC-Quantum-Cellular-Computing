"""
Intent interpreter implementation for the QCC Assembler.

This module provides the IntentInterpreter class, which analyzes
user requests to determine required capabilities and configurations.
"""

import re
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

from .models import IntentAnalysis, RequiredCapability
from .patterns import intentPatterns, capabilityMapping

logger = logging.getLogger(__name__)

class IntentInterpreter:
    """
    Interprets user intent to determine required capabilities.
    
    The IntentInterpreter analyzes natural language requests from users
    and translates them into specific capability requirements and
    configuration parameters.
    
    Attributes:
        pattern_cache (Dict[str, re.Pattern]): Compiled regex patterns
    """
    
    def __init__(self):
        """Initialize the intent interpreter."""
        self.pattern_cache = {}
        for pattern_name, pattern_str in intentPatterns.items():
            self.pattern_cache[pattern_name] = re.compile(pattern_str, re.IGNORECASE)
        
        logger.info("Intent interpreter initialized with %d patterns", len(self.pattern_cache))
        
    async def analyze(self, user_request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a user request to determine required capabilities.
        
        Args:
            user_request: Natural language request from the user
            context: Additional context information
            
        Returns:
            Dictionary containing intent analysis results
        """
        logger.info("Analyzing intent: %s", user_request)
        
        # Initialize context if not provided
        context = context or {}
        
        # Normalize request text
        normalized_request = self._normalize_text(user_request)
        
        # Identify capability requirements
        required_capabilities = self._identify_capabilities(normalized_request, context)
        
        # Identify connections between capabilities
        suggested_connections = self._identify_connections(required_capabilities)
        
        # Create intent analysis result
        intent_analysis = {
            "original_request": user_request,
            "normalized_request": normalized_request,
            "required_capabilities": [cap.name for cap in required_capabilities],
            "capability_details": [cap.to_dict() for cap in required_capabilities],
            "suggested_connections": suggested_connections,
            "analyzed_at": datetime.now().isoformat(),
            "context_used": bool(context),
            "confidence_score": self._calculate_confidence(required_capabilities),
            "use_previous_configurations": True  # Default to using previous configurations
        }
        
        logger.debug("Intent analysis complete: %s", intent_analysis["required_capabilities"])
        return intent_analysis
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for analysis.
        
        Args:
            text: Raw text input
            
        Returns:
            Normalized text
        """
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Expand common abbreviations
        abbreviations = {
            'doc': 'document',
            'pic': 'picture',
            'calc': 'calculator',
            'app': 'application',
            'info': 'information',
            'stats': 'statistics',
            'ui': 'user interface',
            'db': 'database'
        }
        
        for abbr, expansion in abbreviations.items():
            normalized = re.sub(r'\b' + abbr + r'\b', expansion, normalized)
        
        return normalized
    
    def _identify_capabilities(
        self, 
        normalized_request: str,
        context: Dict[str, Any]
    ) -> List[RequiredCapability]:
        """
        Identify required capabilities from the normalized request.
        
        Args:
            normalized_request: Normalized user request
            context: Additional context information
            
        Returns:
            List of required capabilities
        """
        required_capabilities = []
        
        # Check each pattern
        for pattern_name, pattern in self.pattern_cache.items():
            match = pattern.search(normalized_request)
            if match:
                logger.debug("Matched pattern: %s", pattern_name)
                
                # Look up capabilities for this pattern
                if pattern_name in capabilityMapping:
                    for capability_info in capabilityMapping[pattern_name]:
                        capability = RequiredCapability(
                            name=capability_info["name"],
                            parameters=capability_info.get("parameters", {}),
                            priority=capability_info.get("priority", 1),
                            confidence=capability_info.get("confidence", 0.8)
                        )
                        
                        # Apply device-specific adjustments from context
                        if context and "device_info" in context:
                            self._adjust_for_device(capability, context["device_info"])
                        
                        # Add the capability if not already present
                        if not any(cap.name == capability.name for cap in required_capabilities):
                            required_capabilities.append(capability)
        
        # If no capabilities identified, use fallbacks
        if not required_capabilities:
            logger.warning("No capabilities identified, using fallbacks")
            required_capabilities.append(
                RequiredCapability(
                    name="text_generation",
                    parameters={"mode": "informative"},
                    priority=1,
                    confidence=0.5
                )
            )
            
            # If request looks like it might need visuals, add UI capability
            if re.search(r'\b(show|display|visual|graph|chart|picture|image)\b', normalized_request):
                required_capabilities.append(
                    RequiredCapability(
                        name="ui_rendering",
                        parameters={"type": "simple"},
                        priority=2,
                        confidence=0.4
                    )
                )
        
        # Sort capabilities by priority
        required_capabilities.sort(key=lambda cap: cap.priority)
        
        return required_capabilities
    
    def _adjust_for_device(self, capability: RequiredCapability, device_info: Dict[str, Any]) -> None:
        """
        Adjust capability requirements based on device information.
        
        Args:
            capability: Capability to adjust
            device_info: Device information from context
        """
        # Example adjustments based on device capabilities
        
        # Adjust UI rendering based on platform
        if capability.name == "ui_rendering":
            if device_info.get("platform") == "mobile":
                capability.parameters["responsive"] = True
                capability.parameters["compact"] = True
            elif device_info.get("platform") == "web":
                capability.parameters["responsive"] = True
            
        # Adjust media processing based on resources
        if capability.name == "media_processing":
            memory_gb = device_info.get("memory_gb", 4)
            if memory_gb < 2:
                capability.parameters["quality"] = "low"
            elif memory_gb < 8:
                capability.parameters["quality"] = "medium"
            else:
                capability.parameters["quality"] = "high"
            
            if device_info.get("gpu_available"):
                capability.parameters["use_gpu"] = True
    
    def _identify_connections(self, capabilities: List[RequiredCapability]) -> Dict[str, List[str]]:
        """
        Identify suggested connections between capabilities.
        
        Args:
            capabilities: List of required capabilities
            
        Returns:
            Dictionary mapping source capabilities to target capabilities
        """
        connections = {}
        
        # Simple rules for connecting capabilities
        # In a real implementation, this would be more sophisticated
        
        for source_cap in capabilities:
            connections[source_cap.name] = []
            
            # UI should connect to data providers
            if source_cap.name == "ui_rendering":
                for target_cap in capabilities:
                    if target_cap.name in [
                        "text_generation", 
                        "data_analysis", 
                        "media_processing",
                        "file_system"
                    ]:
                        connections[source_cap.name].append(target_cap.name)
            
            # Text generation should connect to data sources
            elif source_cap.name == "text_generation":
                for target_cap in capabilities:
                    if target_cap.name in [
                        "data_analysis",
                        "file_system",
                        "web_search"
                    ]:
                        connections[source_cap.name].append(target_cap.name)
            
            # Data analysis should connect to data sources
            elif source_cap.name == "data_analysis":
                for target_cap in capabilities:
                    if target_cap.name in [
                        "file_system",
                        "database",
                        "web_search"
                    ]:
                        connections[source_cap.name].append(target_cap.name)
        
        return connections
    
    def _calculate_confidence(self, capabilities: List[RequiredCapability]) -> float:
        """
        Calculate overall confidence score for the intent analysis.
        
        Args:
            capabilities: List of required capabilities
            
        Returns:
            Confidence score between 0 and 1
        """
        if not capabilities:
            return 0.0
            
        # Simple average of capability confidences
        return sum(cap.confidence for cap in capabilities) / len(capabilities)

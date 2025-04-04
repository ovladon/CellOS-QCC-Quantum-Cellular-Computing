"""
The core Cell Assembler implementation for Quantum Cellular Computing.

This module provides the primary interface for the assembler, the only
permanent component in the QCC architecture responsible for interpreting
user intent and orchestrating cells into cohesive solutions.
"""

import uuid
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

from qcc.assembler.intent import IntentInterpreter
from qcc.assembler.security import SecurityManager
from qcc.assembler.runtime import CellRuntime
from qcc.quantum_trail import QuantumTrailManager
from qcc.common.exceptions import CellRequestError, SecurityVerificationError
from qcc.common.models import Solution, Cell, CellConfiguration

logger = logging.getLogger(__name__)

class CellAssembler:
    """
    The primary orchestrator for the QCC system.
    
    Responsible for:
    - Interpreting user intent
    - Requesting cells from providers
    - Managing cell lifecycle
    - Orchestrating inter-cell communication
    - Maintaining quantum trails
    
    Attributes:
        assembler_id (str): Unique identifier for this assembler instance
        user_id (str): Anonymous identifier for the user
        provider_urls (List[str]): Endpoints for cell providers
        active_solutions (Dict[str, Solution]): Currently active solutions
        intent_interpreter (IntentInterpreter): Component for user intent analysis
        security_manager (SecurityManager): Component for security verification
        cell_runtime (CellRuntime): Component for cell execution
        quantum_trail (QuantumTrailManager): Component for quantum trail management
        cell_cache (Dict[str, Dict]): Cache of frequently used cells
    """
    
    def __init__(self, user_id: str = "anonymous", provider_urls: List[str] = None):
        """
        Initialize the Cell Assembler.
        
        Args:
            user_id: Anonymous identifier for the user
            provider_urls: List of cell provider endpoints
        """
        self.assembler_id = str(uuid.uuid4())
        self.user_id = user_id
        self.provider_urls = provider_urls or ["https://default-provider.cellcomputing.ai"]
        self.active_solutions = {}
        self.cell_cache = {}
        
        # Initialize core components
        self.intent_interpreter = IntentInterpreter()
        self.security_manager = SecurityManager()
        self.cell_runtime = CellRuntime()
        self.quantum_trail = QuantumTrailManager()
        
        # Track system metrics
        self.start_time = datetime.now()
        self.total_assemblies = 0
        self.total_cells_requested = 0
        
        logger.info(f"Cell Assembler initialized with ID {self.assembler_id}")
    
    async def assemble_solution(self, user_request: str, context: Dict[str, Any] = None) -> Solution:
        """
        Interpret user intent and assemble cells into a solution.
        
        Args:
            user_request: Natural language description of user need
            context: Additional context information (device, environment, etc.)
            
        Returns:
            Solution object representing the assembled cells
            
        Raises:
            CellRequestError: If required cells cannot be obtained
            SecurityVerificationError: If cell verification fails
        """
        start_time = time.time()
        logger.info(f"Assembling solution for request: {user_request}")
        self.total_assemblies += 1
        
        # Prepare context if not provided
        context = context or {}
        context.update({
            "timestamp": datetime.now().isoformat(),
            "device_info": context.get("device_info", self._get_device_info()),
            "assembler_id": self.assembler_id
        })
        
        # Interpret user intent
        intent_analysis = await self.intent_interpreter.analyze(user_request, context)
        logger.debug(f"Intent analysis: {intent_analysis}")
        
        # Determine required capabilities
        required_capabilities = intent_analysis["required_capabilities"]
        if not required_capabilities:
            logger.warning("No capabilities identified from user request")
            required_capabilities = ["text_generation"]  # Fallback capability
            
        # Generate quantum trail for this request
        quantum_signature = await self.quantum_trail.generate_signature(
            user_id=self.user_id,
            intent=intent_analysis,
            context=context
        )
        logger.debug(f"Generated quantum signature: {quantum_signature[:16]}...")
        
        # Try to find similar configurations in quantum trail
        similar_configs = await self.quantum_trail.find_similar_configurations(
            capabilities=required_capabilities,
            context_similarity=context,
            max_results=3
        )
        
        # If similar configurations found, use the highest performing one
        cell_configuration = None
        if similar_configs and intent_analysis.get("use_previous_configurations", True):
            cell_configuration = self._select_best_configuration(similar_configs)
            logger.info(f"Using similar configuration from quantum trail: {cell_configuration.id}")
        
        # Request cells from providers
        try:
            if cell_configuration:
                # Use existing configuration as guide
                cells = await self._request_cells_by_configuration(
                    cell_configuration, 
                    quantum_signature
                )
            else:
                # Request based on capabilities
                cells = await self._request_cells_by_capabilities(
                    required_capabilities, 
                    quantum_signature, 
                    context
                )
        except CellRequestError as e:
            logger.error(f"Failed to request cells: {e}")
            raise
        
        # Verify cell security
        try:
            await self.security_manager.verify_cells(cells, quantum_signature)
        except SecurityVerificationError as e:
            logger.error(f"Security verification failed: {e}")
            # Release any cells already acquired
            for cell_id, cell in cells.items():
                await self.cell_runtime.release_cell(cell)
            raise
        
        # Establish cell connections based on intent or configuration
        if cell_configuration:
            connection_map = cell_configuration.connection_map
        else:
            connection_map = intent_analysis.get("suggested_connections", {})
            
        for source, targets in connection_map.items():
            if source in cells:
                for target in targets:
                    if target in cells:
                        await self.cell_runtime.connect_cells(cells[source], cells[target])
                    else:
                        logger.warning(f"Cannot connect to missing cell: {target}")
            else:
                logger.warning(f"Cannot connect from missing cell: {source}")
        
        # Activate cells
        for cell_id, cell in cells.items():
            await self.cell_runtime.activate_cell(cell)
        
        # Create solution object
        solution_id = str(uuid.uuid4())
        solution = Solution(
            id=solution_id,
            cells=cells,
            quantum_signature=quantum_signature,
            created_at=datetime.now().isoformat(),
            intent=intent_analysis,
            status="active",
            context=context
        )
        
        # Store active solution
        self.active_solutions[solution_id] = solution
        
        # Record assembly time
        assembly_time_ms = int((time.time() - start_time) * 1000)
        
        # Record successful assembly in quantum trail
        await self.quantum_trail.record_assembly(
            quantum_signature=quantum_signature,
            solution_id=solution_id,
            cell_ids=list(cells.keys()),
            connection_map=connection_map,
            performance_metrics={"assembly_time_ms": assembly_time_ms}
        )
        
        logger.info(f"Solution assembled: {solution_id} with {len(cells)} cells in {assembly_time_ms}ms")
        return solution
    
    async def release_solution(self, solution_id: str) -> bool:
        """
        Release all cells associated with a solution.
        
        Args:
            solution_id: Identifier of the solution to release
            
        Returns:
            Success indicator
        """
        logger.info(f"Releasing solution: {solution_id}")
        
        if solution_id not in self.active_solutions:
            logger.warning(f"Attempted to release unknown solution: {solution_id}")
            return False
        
        solution = self.active_solutions[solution_id]
        usage_time_ms = 0
        
        # Calculate usage time
        if "created_at" in solution:
            created_at = datetime.fromisoformat(solution["created_at"])
            usage_time_ms = int((datetime.now() - created_at).total_seconds() * 1000)
        
        # Deactivate and release all cells
        for cell_id, cell in solution.cells.items():
            try:
                await self.cell_runtime.deactivate_cell(cell)
                
                # Decide whether to cache this cell
                if self._should_cache_cell(cell, solution):
                    self._add_to_cache(cell)
                else:
                    await self.cell_runtime.release_cell(cell)
                    
            except Exception as e:
                logger.error(f"Error releasing cell {cell_id}: {e}")
        
        # Update quantum trail with usage information
        await self.quantum_trail.update_assembly_record(
            quantum_signature=solution.quantum_signature,
            solution_id=solution_id,
            status="released",
            performance_metrics={
                "total_usage_time_ms": usage_time_ms,
                "memory_peak_mb": solution.get("memory_peak_mb", 0),
                "cpu_usage_avg": solution.get("cpu_usage_avg", 0)
            }
        )
        
        # Remove from active solutions
        del self.active_solutions[solution_id]
        
        return True
    
    async def _request_cells_by_capabilities(
        self, 
        capabilities: List[str], 
        quantum_signature: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Cell]:
        """
        Request cells from providers based on required capabilities.
        
        Args:
            capabilities: List of required cell capabilities
            quantum_signature: Quantum signature for security
            context: Additional context information
            
        Returns:
            Dictionary of cell objects keyed by cell ID
        """
        logger.info(f"Requesting cells with capabilities: {capabilities}")
        
        cells = {}
        self.total_cells_requested += len(capabilities)
        
        # Check cache first for each capability
        for capability in capabilities:
            cached_cell = self._get_from_cache(capability, context)
            if cached_cell:
                cells[cached_cell.id] = cached_cell
                logger.info(f"Using cached cell {cached_cell.id} for capability {capability}")
                continue
            
            # Determine best provider for this capability
            provider_url = self._select_provider_for_capability(capability)
            
            # Request cell from provider
            try:
                cell = await self._request_cell_from_provider(
                    provider_url, 
                    capability, 
                    quantum_signature,
                    context
                )
                cells[cell.id] = cell
                logger.info(f"Received cell {cell.id} for capability {capability} from {provider_url}")
            except CellRequestError as e:
                logger.error(f"Failed to request cell for capability {capability}: {e}")
                # Try backup provider if available
                if len(self.provider_urls) > 1:
                    backup_provider = [p for p in self.provider_urls if p != provider_url][0]
                    try:
                        logger.info(f"Trying backup provider {backup_provider} for capability {capability}")
                        cell = await self._request_cell_from_provider(
                            backup_provider, 
                            capability, 
                            quantum_signature,
                            context
                        )
                        cells[cell.id] = cell
                        logger.info(f"Received cell {cell.id} from backup provider {backup_provider}")
                    except CellRequestError as e2:
                        logger.error(f"Backup provider also failed: {e2}")
                        raise CellRequestError(f"Failed to request cell for {capability} from all providers")
        
        if not cells:
            raise CellRequestError("Failed to obtain any required cells")
            
        return cells
    
    async def _request_cells_by_configuration(
        self, 
        configuration: CellConfiguration, 
        quantum_signature: str
    ) -> Dict[str, Cell]:
        """
        Request cells based on a previous successful configuration.
        
        Args:
            configuration: Previous cell configuration to replicate
            quantum_signature: Quantum signature for security
            
        Returns:
            Dictionary of cell objects keyed by cell ID
        """
        logger.info(f"Requesting cells based on configuration: {configuration.id}")
        
        cells = {}
        self.total_cells_requested += len(configuration.cell_specs)
        
        for cell_spec in configuration.cell_specs:
            provider_url = cell_spec.get("provider_url") or self.provider_urls[0]
            
            try:
                cell = await self._request_specific_cell(
                    provider_url,
                    cell_spec["cell_type"],
                    cell_spec.get("version"),
                    quantum_signature,
                    cell_spec.get("parameters", {})
                )
                cells[cell.id] = cell
                logger.info(f"Received cell {cell.id} of type {cell_spec['cell_type']} from {provider_url}")
            except CellRequestError as e:
                logger.error(f"Failed to request cell: {e}")
                # Try alternative provider
                if len(self.provider_urls) > 1:
                    backup_provider = [p for p in self.provider_urls if p != provider_url][0]
                    try:
                        cell = await self._request_specific_cell(
                            backup_provider,
                            cell_spec["cell_type"],
                            cell_spec.get("version"),
                            quantum_signature,
                            cell_spec.get("parameters", {})
                        )
                        cells[cell.id] = cell
                    except CellRequestError:
                        # Fall back to capability-based request
                        try:
                            cell = await self._request_cell_from_provider(
                                backup_provider,
                                cell_spec["capability"],
                                quantum_signature,
                                cell_spec.get("parameters", {})
                            )
                            cells[cell.id] = cell
                        except CellRequestError as e3:
                            logger.error(f"All fallback options failed for cell: {e3}")
        
        if not cells:
            raise CellRequestError("Failed to obtain any cells from configuration")
            
        return cells
    
    async def _request_cell_from_provider(
        self, 
        provider_url: str, 
        capability: str, 
        quantum_signature: str, 
        context: Dict[str, Any] = None
    ) -> Cell:
        """
        Request a cell with a specific capability from a provider.
        
        Args:
            provider_url: URL of the cell provider
            capability: Required capability
            quantum_signature: Quantum signature for security
            context: Additional context information
            
        Returns:
            Cell object
            
        Raises:
            CellRequestError: If the cell request fails
        """
        # In a real implementation, this would make API calls to cell providers
        # This is a simplified implementation for demonstration
        
        # Simulate network delay
        await asyncio.sleep(0.2)
        
        # Simulate cell response
        cell_id = str(uuid.uuid4())
        cell = Cell(
            id=cell_id,
            capability=capability,
            provider=provider_url,
            version="1.0.0",
            quantum_signature=quantum_signature,
            status="initialized",
            created_at=datetime.now().isoformat(),
            context=context or {}
        )
        
        return cell
    
    async def _request_specific_cell(
        self, 
        provider_url: str, 
        cell_type: str, 
        version: str,
        quantum_signature: str, 
        parameters: Dict[str, Any]
    ) -> Cell:
        """
        Request a specific cell type and version from a provider.
        
        Args:
            provider_url: URL of the cell provider
            cell_type: Specific cell type identifier
            version: Requested version of the cell
            quantum_signature: Quantum signature for security
            parameters: Additional parameters for cell initialization
            
        Returns:
            Cell object
            
        Raises:
            CellRequestError: If the cell request fails
        """
        # In a real implementation, this would make API calls to cell providers
        # This is a simplified implementation for demonstration
        
        # Simulate network delay
        await asyncio.sleep(0.25)
        
        # Simulate cell response
        cell_id = str(uuid.uuid4())
        cell = Cell(
            id=cell_id,
            cell_type=cell_type,
            version=version or "latest",
            provider=provider_url,
            quantum_signature=quantum_signature,
            status="initialized",
            created_at=datetime.now().isoformat(),
            parameters=parameters
        )
        
        return cell
    
    def _select_provider_for_capability(self, capability: str) -> str:
        """
        Select the most appropriate provider for a given capability.
        
        In a real implementation, this would consider provider reliability,
        performance, cost, and other factors.
        
        Args:
            capability: The required capability
            
        Returns:
            URL of the selected provider
        """
        # Simple implementation that just returns the first provider
        # In a real system, this would be much more sophisticated
        return self.provider_urls[0]
    
    def _select_best_configuration(self, configurations: List[CellConfiguration]) -> CellConfiguration:
        """
        Select the best configuration from similar past configurations.
        
        Args:
            configurations: List of potential configurations
            
        Returns:
            The selected configuration
        """
        # Sort by performance score (higher is better)
        sorted_configs = sorted(
            configurations, 
            key=lambda c: c.performance_score if hasattr(c, 'performance_score') else 0,
            reverse=True
        )
        
        # Return the highest scoring configuration
        return sorted_configs[0]
    
    def _should_cache_cell(self, cell: Cell, solution: Solution) -> bool:
        """
        Determine whether a cell should be cached after use.
        
        Args:
            cell: The cell to consider caching
            solution: The solution the cell was part of
            
        Returns:
            True if the cell should be cached, False otherwise
        """
        # Cache policies could include:
        # - Frequently used capabilities
        # - Cells that took a long time to load
        # - Cells from solutions with high satisfaction scores
        
        # Simple example: cache cells that are part of core capabilities
        core_capabilities = ["file_system", "ui_rendering", "text_generation"]
        return cell.capability in core_capabilities
    
    def _add_to_cache(self, cell: Cell) -> None:
        """
        Add a cell to the cache.
        
        Args:
            cell: The cell to cache
        """
        # Check if we already have this capability cached
        if cell.capability in self.cell_cache:
            # Replace if this cell is newer
            cached_cell = self.cell_cache[cell.capability]
            cached_created_at = datetime.fromisoformat(cached_cell["created_at"])
            cell_created_at = datetime.fromisoformat(cell.created_at)
            
            if cell_created_at > cached_created_at:
                logger.debug(f"Replacing cached cell for capability {cell.capability}")
                self.cell_cache[cell.capability] = cell
        else:
            # Add new capability to cache
            logger.debug(f"Adding cell {cell.id} to cache for capability {cell.capability}")
            self.cell_cache[cell.capability] = cell
            
        # Implement cache size limiting if needed
        if len(self.cell_cache) > 20:  # Example limit
            # Remove oldest cell
            oldest_capability = min(
                self.cell_cache.keys(),
                key=lambda cap: datetime.fromisoformat(self.cell_cache[cap].created_at)
            )
            logger.debug(f"Cache full, removing oldest cell for capability {oldest_capability}")
            removed_cell = self.cell_cache.pop(oldest_capability)
            asyncio.create_task(self.cell_runtime.release_cell(removed_cell))
    
    def _get_from_cache(self, capability: str, context: Dict[str, Any]) -> Optional[Cell]:
        """
        Retrieve a cell from the cache if available.
        
        Args:
            capability: Required capability
            context: Current context information
            
        Returns:
            Cached cell or None if not available
        """
        if capability in self.cell_cache:
            cell = self.cell_cache[capability]
            
            # Check if the cached cell is compatible with current context
            if self._is_compatible_with_context(cell, context):
                logger.debug(f"Cache hit for capability {capability}")
                return cell
                
        return None
    
    def _is_compatible_with_context(self, cell: Cell, context: Dict[str, Any]) -> bool:
        """
        Check if a cached cell is compatible with the current context.
        
        Args:
            cell: Cached cell to check
            context: Current context information
            
        Returns:
            True if compatible, False otherwise
        """
        # Example compatibility checks:
        # - Device compatibility
        # - Required resources availability
        # - Version compatibility
        
        # Simple implementation that always returns True
        return True
    
    def _get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the current device.
        
        Returns:
            Dictionary with device information
        """
        # In a real implementation, this would gather actual device information
        return {
            "platform": "linux",  # Example value
            "memory_gb": 8,       # Example value
            "cpu_cores": 4,       # Example value
            "gpu_available": False # Example value
        }
        
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the assembler.
        
        Returns:
            Dictionary with status information
        """
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "assembler_id": self.assembler_id,
            "status": "active",
            "uptime_seconds": uptime_seconds,
            "active_solutions": len(self.active_solutions),
            "cached_cells": len(self.cell_cache),
            "total_assemblies": self.total_assemblies,
            "total_cells_requested": self.total_cells_requested
        }

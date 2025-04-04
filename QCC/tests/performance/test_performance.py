"""
General performance tests for the QCC system.

These tests establish baseline performance metrics for core QCC operations
and help identify bottlenecks in the system.
"""

import pytest
import asyncio
import os
import sys
import time
import json
import logging
import tempfile
import random
from pathlib import Path
import resource

from . import Timer, record_benchmark, PERFORMANCE_TEST_ITERATIONS

from qcc.assembler.core.assembler import CellAssembler
from qcc.providers.repository.manager import create_repository_manager
from qcc.common.models import Solution, Cell, CellConfiguration
from qcc.common.exceptions import CellRequestError

# Configure logging
logger = logging.getLogger(__name__)

# Test fixtures and utilities
@pytest.fixture
async def setup_benchmark_environment():
    """Set up an environment for benchmarking with pre-configured components."""
    # Create temporary directories
    temp_dir = tempfile.mkdtemp(prefix="qcc_benchmark_")
    os.makedirs(os.path.join(temp_dir, "cells"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "quantum_trail"), exist_ok=True)
    
    # Initialize repository manager with test cells
    repo_manager = await create_repository_manager(
        storage_path=os.path.join(temp_dir, "cells")
    )
    
    # Register test cells
    await register_benchmark_cells(repo_manager)
    
    # Initialize assembler with minimal components
    assembler = CellAssembler(
        user_id="benchmark_user",
        provider_urls=["http://localhost:8081"]  # Will be mocked
    )
    
    # Mock cell provider requests to use our repository manager
    original_request_cell = assembler._request_cell_from_provider
    
    async def mock_request_cell(provider_url, capability, quantum_signature, context):
        cell_data = await repo_manager.get_cell_for_capability(capability, None, context)
        return Cell(
            id=cell_data["id"],
            cell_type=cell_data["cell_type"],
            capability=capability,
            provider=provider_url,
            quantum_signature=quantum_signature,
            status="initialized",
            context=context or {}
        )
    
    assembler._request_cell_from_provider = mock_request_cell
    
    try:
        yield {
            "assembler": assembler,
            "repo_manager": repo_manager,
            "temp_dir": temp_dir
        }
    finally:
        # Restore original method
        assembler._request_cell_from_provider = original_request_cell
        
        # Clean up
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

async def register_benchmark_cells(repo_manager):
    """Register cells for benchmarking with the repository manager."""
    # Create multiple cells for each capability for realistic benchmarks
    capabilities = [
        "text_processing", "file_operations", "user_interface", 
        "data_visualization", "network_interface", "media_playback",
        "search_engine", "calculator", "translation"
    ]
    
    for capability in capabilities:
        for version in range(1, 4):  # Create 3 versions of each
            await repo_manager.register_cell(
                cell_type=f"{capability}_cell",
                capability=capability,
                version=f"1.{version}.0",
                package={
                    "type": "mock",
                    "capabilities": [capability]
                },
                metadata={
                    "description": f"{capability} cell for benchmarking",
                    "resource_requirements": {
                        "memory_mb": 10 + random.randint(0, 20),
                        "cpu_percent": 5 + random.randint(0, 10)
                    }
                }
            )

def generate_test_intent(complexity=1):
    """Generate a test intent with the specified complexity."""
    intents = [
        "Create a text document",
        "Open and edit a text file",
        "Analyze some data and create a visualization",
        "Search for information and compile a report",
        "Translate a document and save it in multiple formats",
        "Stream a media file while tracking network performance",
        "Create a spreadsheet with complex calculations and graphs",
        "Design a user interface for a data entry application"
    ]
    
    # Simple intent (single capability)
    if complexity == 1:
        return random.choice(intents)
    
    # Medium complexity (2-3 capabilities)
    if complexity == 2:
        return random.choice([
            "Create a document and visualize the data it contains",
            "Search for information and compile it into a report",
            "Open a file, translate its content, and save the result",
            "Calculate statistics from input data and create charts"
        ])
    
    # High complexity (4+ capabilities)
    return random.choice([
        "Search the web for data, analyze it, create visualizations, and compile a report",
        "Open multiple media files, process them, apply transformations, and save in different formats",
        "Design a user interface that allows editing documents, visualizing data, and sharing results",
        "Create a project that requires text editing, data analysis, visualization, and collaborative editing"
    ])

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_cell_retrieval_performance(setup_benchmark_environment):
    """Benchmark cell retrieval from repository."""
    env = await setup_benchmark_environment
    repo_manager = env["repo_manager"]
    
    capabilities = [
        "text_processing", "file_operations", "user_interface", 
        "data_visualization", "network_interface", "media_playback"
    ]
    
    results = {
        "cell_retrieval_times_ms": [],
        "avg_retrieval_time_ms": 0,
        "min_retrieval_time_ms": 0,
        "max_retrieval_time_ms": 0
    }
    
    # Warm up
    for capability in capabilities:
        await repo_manager.get_cell_for_capability(capability)
    
    # Benchmark
    for i in range(PERFORMANCE_TEST_ITERATIONS):
        for capability in capabilities:
            with Timer(f"Cell retrieval for {capability}") as timer:
                await repo_manager.get_cell_for_capability(capability)
            
            results["cell_retrieval_times_ms"].append(timer.elapsed_ms())
    
    # Calculate stats
    if results["cell_retrieval_times_ms"]:
        results["avg_retrieval_time_ms"] = sum(results["cell_retrieval_times_ms"]) / len(results["cell_retrieval_times_ms"])
        results["min_retrieval_time_ms"] = min(results["cell_retrieval_times_ms"])
        results["max_retrieval_time_ms"] = max(results["cell_retrieval_times_ms"])
    
    # Record benchmark results
    record_benchmark("cell_retrieval_performance", results)
    
    # Assertions for test pass/fail
    assert results["avg_retrieval_time_ms"] < 100, "Average cell retrieval time should be under 100ms"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_solution_assembly_performance(setup_benchmark_environment):
    """Benchmark the solution assembly process."""
    env = await setup_benchmark_environment
    assembler = env["assembler"]
    
    # Prepare for the benchmark
    complexity_levels = [1, 2, 3]  # Simple, medium, high complexity
    iterations_per_level = PERFORMANCE_TEST_ITERATIONS
    
    results = {
        "assembly_times_ms": [],
        "by_complexity": {
            "simple": {"times_ms": [], "avg_ms": 0},
            "medium": {"times_ms": [], "avg_ms": 0},
            "high": {"times_ms": [], "avg_ms": 0}
        },
        "avg_assembly_time_ms": 0,
        "min_assembly_time_ms": 0,
        "max_assembly_time_ms": 0,
        "cells_per_solution": []
    }
    
    # For each complexity level
    for complexity in complexity_levels:
        complexity_name = ["simple", "medium", "high"][complexity-1]
        logger.info(f"Benchmarking {complexity_name} complexity solutions")
        
        for i in range(iterations_per_level):
            # Generate a test intent
            intent = generate_test_intent(complexity)
            
            # Measure assembly time
            with Timer(f"Solution assembly ({complexity_name})") as timer:
                solution = await assembler.assemble_solution(intent)
                
            assembly_time = timer.elapsed_ms()
            results["assembly_times_ms"].append(assembly_time)
            results["by_complexity"][complexity_name]["times_ms"].append(assembly_time)
            results["cells_per_solution"].append(len(solution.cells))
            
            # Release the solution
            await assembler.release_solution(solution.id)
    
    # Calculate statistics
    if results["assembly_times_ms"]:
        results["avg_assembly_time_ms"] = sum(results["assembly_times_ms"]) / len(results["assembly_times_ms"])
        results["min_assembly_time_ms"] = min(results["assembly_times_ms"])
        results["max_assembly_time_ms"] = max(results["assembly_times_ms"])
        
        for complexity in ["simple", "medium", "high"]:
            times = results["by_complexity"][complexity]["times_ms"]
            if times:
                results["by_complexity"][complexity]["avg_ms"] = sum(times) / len(times)
        
        results["avg_cells_per_solution"] = sum(results["cells_per_solution"]) / len(results["cells_per_solution"])
    
    # Record benchmark results
    record_benchmark("solution_assembly_performance", results)
    
    # Assertions for test pass/fail
    assert results["avg_assembly_time_ms"] < 500, "Average solution assembly time should be under 500ms"
    assert results["by_complexity"]["high"]["avg_ms"] < 1000, "Complex solution assembly time should be under 1000ms"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_solution_concurrent_assembly(setup_benchmark_environment):
    """Benchmark concurrent solution assembly."""
    env = await setup_benchmark_environment
    assembler = env["assembler"]
    
    concurrency_levels = [1, 5, 10, 20]
    results = {
        "concurrency": {},
        "summary": {
            "avg_assembly_time_ms": {},
            "throughput_solutions_per_second": {}
        }
    }
    
    for concurrency in concurrency_levels:
        logger.info(f"Benchmarking with concurrency level {concurrency}")
        
        # Create tasks for concurrent assemblies
        intents = [generate_test_intent(random.randint(1, 3)) for _ in range(concurrency)]
        assembly_times = []
        solutions = []
        
        start_time = time.time()
        
        async def assemble_and_time(intent):
            with Timer(f"Concurrent assembly for '{intent}'") as timer:
                solution = await assembler.assemble_solution(intent)
                assembly_times.append(timer.elapsed_ms())
                solutions.append(solution)
        
        # Execute concurrent assemblies
        tasks = [assemble_and_time(intent) for intent in intents]
        await asyncio.gather(*tasks)
        
        total_time = (time.time() - start_time) * 1000  # ms
        
        # Record metrics for this concurrency level
        results["concurrency"][concurrency] = {
            "assembly_times_ms": assembly_times,
            "avg_assembly_time_ms": sum(assembly_times) / len(assembly_times) if assembly_times else 0,
            "min_assembly_time_ms": min(assembly_times) if assembly_times else 0,
            "max_assembly_time_ms": max(assembly_times) if assembly_times else 0,
            "total_time_ms": total_time,
            "throughput_solutions_per_second": (concurrency / total_time) * 1000 if total_time > 0 else 0
        }
        
        # Summary stats
        results["summary"]["avg_assembly_time_ms"][concurrency] = results["concurrency"][concurrency]["avg_assembly_time_ms"]
        results["summary"]["throughput_solutions_per_second"][concurrency] = results["concurrency"][concurrency]["throughput_solutions_per_second"]
        
        # Release all solutions
        for solution in solutions:
            await assembler.release_solution(solution.id)
    
    # Record benchmark results
    record_benchmark("solution_concurrent_assembly", results)
    
    # Assertions for test pass/fail
    assert results["summary"]["throughput_solutions_per_second"][concurrency_levels[-1]] > 0, "Should have positive throughput"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_memory_usage(setup_benchmark_environment):
    """Benchmark memory usage during solution assembly and execution."""
    env = await setup_benchmark_environment
    assembler = env["assembler"]
    
    iterations = PERFORMANCE_TEST_ITERATIONS
    results = {
        "baseline_memory_kb": 0,
        "peak_memory_kb": 0,
        "memory_increase_kb": 0,
        "per_solution_memory_kb": [],
        "memory_growth_pattern": []
    }
    
    # Measure baseline memory usage
    baseline_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    results["baseline_memory_kb"] = baseline_memory
    logger.info(f"Baseline memory usage: {baseline_memory} KB")
    
    # Create and retain solutions to measure memory growth
    solutions = []
    
    for i in range(iterations):
        # Generate a test intent with random complexity
        intent = generate_test_intent(random.randint(1, 3))
        
        # Measure before solution assembly
        before_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Assemble solution
        solution = await assembler.assemble_solution(intent)
        solutions.append(solution)
        
        # Measure after solution assembly
        after_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        solution_memory = after_memory - before_memory
        
        results["per_solution_memory_kb"].append(solution_memory)
        results["memory_growth_pattern"].append(after_memory)
        
        logger.info(f"Solution {i+1} assembled, memory usage: {after_memory} KB, increase: {solution_memory} KB")
    
    # Record peak memory
    peak_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    results["peak_memory_kb"] = peak_memory
    results["memory_increase_kb"] = peak_memory - baseline_memory
    
    # Calculate average memory per solution
    if results["per_solution_memory_kb"]:
        results["avg_memory_per_solution_kb"] = sum(results["per_solution_memory_kb"]) / len(results["per_solution_memory_kb"])
    
    # Release all solutions
    for solution in solutions:
        await assembler.release_solution(solution.id)
    
    # Measure memory after release
    after_release_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    results["memory_after_release_kb"] = after_release_memory
    results["memory_not_reclaimed_kb"] = after_release_memory - baseline_memory
    
    logger.info(f"Memory after releasing all solutions: {after_release_memory} KB")
    logger.info(f"Memory not reclaimed: {after_release_memory - baseline_memory} KB")
    
    # Record benchmark results
    record_benchmark("memory_usage", results)

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_quantum_trail_performance(setup_benchmark_environment):
    """Benchmark quantum trail generation and lookup performance."""
    env = await setup_benchmark_environment
    assembler = env["assembler"]
    
    # Replace with a testable quantum trail component to measure specific operations
    original_quantum_trail = assembler.quantum_trail
    
    results = {
        "signature_generation_ms": [],
        "record_assembly_ms": [],
        "find_similar_configurations_ms": [],
        "update_assembly_record_ms": [],
        "averages": {}
    }
    
    try:
        # Mock the quantum trail methods to measure performance
        class BenchmarkableQuantumTrail:
            async def generate_signature(self, user_id, intent, context):
                with Timer("Quantum signature generation") as timer:
                    signature = f"qt-{user_id}-{time.time()}"
                results["signature_generation_ms"].append(timer.elapsed_ms())
                return signature
            
            async def record_assembly(self, quantum_signature, solution_id, cell_ids, connection_map, performance_metrics):
                with Timer("Record assembly") as timer:
                    # Simulate recording by writing to a temp file
                    record = {
                        "quantum_signature": quantum_signature,
                        "solution_id": solution_id,
                        "cell_ids": cell_ids,
                        "connection_map": connection_map,
                        "performance_metrics": performance_metrics
                    }
                    with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
                        json.dump(record, f)
                results["record_assembly_ms"].append(timer.elapsed_ms())
                return True
            
            async def find_similar_configurations(self, capabilities, context_similarity, max_results):
                with Timer("Find similar configurations") as timer:
                    # Simulate lookup time
                    await asyncio.sleep(0.005)  # Simulate 5ms lookup
                results["find_similar_configurations_ms"].append(timer.elapsed_ms())
                return []
            
            async def update_assembly_record(self, quantum_signature, solution_id, status, performance_metrics):
                with Timer("Update assembly record") as timer:
                    # Simulate update by writing to a temp file
                    record = {
                        "quantum_signature": quantum_signature,
                        "solution_id": solution_id,
                        "status": status,
                        "performance_metrics": performance_metrics
                    }
                    with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
                        json.dump(record, f)
                results["update_assembly_record_ms"].append(timer.elapsed_ms())
                return True
        
        # Replace the quantum trail with our benchmarkable implementation
        assembler.quantum_trail = BenchmarkableQuantumTrail()
        
        # Perform assembly operations to measure quantum trail performance
        for i in range(PERFORMANCE_TEST_ITERATIONS):
            intent = generate_test_intent(random.randint(1, 3))
            
            # Assembly will trigger various quantum trail operations
            solution = await assembler.assemble_solution(intent)
            
            # Release will trigger update_assembly_record
            await assembler.release_solution(solution.id)
        
        # Calculate averages
        for metric in ["signature_generation_ms", "record_assembly_ms", "find_similar_configurations_ms", "update_assembly_record_ms"]:
            if results[metric]:
                results["averages"][f"avg_{metric}"] = sum(results[metric]) / len(results[metric])
        
        # Record benchmark results
        record_benchmark("quantum_trail_performance", results)
        
        # Assertions for test pass/fail
        for metric in results["averages"]:
            assert results["averages"][metric] < 100, f"{metric} should be under 100ms on average"
    
    finally:
        # Restore original quantum trail
        assembler.quantum_trail = original_quantum_trail

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_solution_caching_benefit(setup_benchmark_environment):
    """Benchmark the performance benefit of cell caching."""
    env = await setup_benchmark_environment
    assembler = env["assembler"]
    
    # Enable caching
    assembler.cache_enabled = True
    
    results = {
        "cold_start_ms": [],
        "warm_start_ms": [],
        "improvement_percentage": 0
    }
    
    # Fixed set of intents to ensure consistency
    intents = [
        "Create a text document",
        "Visualize some data",
        "Search for information",
        "Edit a file"
    ]
    
    # First pass - cold start (no cached cells)
    logger.info("Measuring cold start performance...")
    for intent in intents:
        with Timer(f"Cold start: {intent}") as timer:
            solution = await assembler.assemble_solution(intent)
        
        results["cold_start_ms"].append(timer.elapsed_ms())
        await assembler.release_solution(solution.id)
    
    # Second pass - warm start (with cached cells)
    logger.info("Measuring warm start performance...")
    for intent in intents:
        with Timer(f"Warm start: {intent}") as timer:
            solution = await assembler.assemble_solution(intent)
        
        results["warm_start_ms"].append(timer.elapsed_ms())
        await assembler.release_solution(solution.id)
    
    # Calculate statistics
    if results["cold_start_ms"] and results["warm_start_ms"]:
        results["avg_cold_start_ms"] = sum(results["cold_start_ms"]) / len(results["cold_start_ms"])
        results["avg_warm_start_ms"] = sum(results["warm_start_ms"]) / len(results["warm_start_ms"])
        
        if results["avg_cold_start_ms"] > 0:
            results["improvement_percentage"] = ((results["avg_cold_start_ms"] - results["avg_warm_start_ms"]) / results["avg_cold_start_ms"]) * 100
    
    # Record benchmark results
    record_benchmark("solution_caching_benefit", results)
    
    # Assertions for test pass/fail
    assert results["improvement_percentage"] > 0, "Caching should provide performance improvement"

if __name__ == "__main__":
    # This allows running just this test module
    pytest.main(["-xvs", __file__])

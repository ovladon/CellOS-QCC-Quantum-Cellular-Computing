"""
QCC Performance Tests

This package contains performance benchmarks and tests for the Quantum Cellular Computing (QCC) project.
Performance tests focus on measuring and optimizing the speed, resource usage, and scalability
of the QCC system under various conditions.

These tests are designed to:
- Establish performance baselines
- Identify bottlenecks
- Verify performance improvements
- Ensure the system meets performance requirements
- Test the system under load and stress conditions

Test modules in this package:
- test_performance.py: General performance metrics
- test_assembler_performance.py: Benchmarks for the assembler component
- test_cell_performance.py: Performance tests for different cell types
- test_scaling.py: System scaling tests (concurrent users, large operations)
- test_resource_usage.py: Memory, CPU, and storage utilization tests
"""

import os
import sys
import logging
import time
from pathlib import Path
from datetime import datetime

# Add project root to path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure logging for performance tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'performance_tests.log'))
    ]
)

# Setup performance test constants and utilities
PERFORMANCE_TEST_ITERATIONS = 10  # Default number of iterations for benchmarks
PERFORMANCE_TEST_DATA_DIR = Path(__file__).parent / "data"
PERFORMANCE_RESULTS_DIR = Path(__file__).parent / "results"

# Create results directory if it doesn't exist
PERFORMANCE_RESULTS_DIR.mkdir(exist_ok=True, parents=True)

# Simple timer function for benchmarking
class Timer:
    def __init__(self, name="Operation"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        logging.info(f"{self.name} completed in {self.elapsed_ms():.2f} ms")
    
    def elapsed_ms(self):
        """Return elapsed time in milliseconds."""
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time is not None else time.time()
        return (end - self.start_time) * 1000

# Function to record benchmark results
def record_benchmark(test_name, metrics):
    """
    Record benchmark results to a JSON file.
    
    Args:
        test_name: Name of the test
        metrics: Dictionary of performance metrics
    """
    import json
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = PERFORMANCE_RESULTS_DIR / f"{test_name}_{timestamp}.json"
    
    # Add timestamp to metrics
    metrics["timestamp"] = timestamp
    metrics["test_name"] = test_name
    
    with open(result_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    logging.info(f"Benchmark results saved to {result_file}")

#!/usr/bin/env python3
"""
Main entry point for the Quantum Cellular Computing (QCC) framework.
This script initializes all core components and starts the QCC system.
"""

import os
import sys
import logging
import argparse
import asyncio
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qcc.config import load_config
from qcc.assembler.core.assembler import CellAssembler
from qcc.providers.repository.manager import ProviderManager
from qcc.quantum_trail.blockchain.ledger import QuantumTrailLedger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "qcc.log"))
    ]
)

logger = logging.getLogger("qcc.main")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="QCC: Quantum Cellular Computing")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-server", action="store_true", help="Don't start the API server")
    parser.add_argument("--cell-dir", help="Directory containing cell implementations")
    return parser.parse_args()

async def initialize_system(config_path, cell_dir=None):
    """Initialize all QCC system components."""
    logger.info("Initializing QCC system...")
    
    # Load configuration
    config = load_config(config_path)
    
    if cell_dir:
        config["cells"]["directory"] = cell_dir
    
    # Initialize quantum trail system
    quantum_trail = QuantumTrailLedger(
        blockchain_path=config["quantum_trail"]["blockchain_path"],
        encryption_key=config["quantum_trail"]["encryption_key"]
    )
    await quantum_trail.initialize()
    
    # Initialize provider manager
    provider_manager = ProviderManager(
        provider_urls=config["providers"]["urls"],
        cache_dir=config["providers"]["cache_dir"]
    )
    await provider_manager.initialize()
    
    # Initialize assembler
    assembler = CellAssembler(
        user_id=config.get("user_id", "anonymous"),
        provider_manager=provider_manager,
        quantum_trail=quantum_trail,
        config=config["assembler"]
    )
    await assembler.initialize()
    
    return {
        "config": config,
        "quantum_trail": quantum_trail,
        "provider_manager": provider_manager,
        "assembler": assembler
    }

async def run_example(components):
    """Run a simple example to demonstrate the QCC system."""
    assembler = components["assembler"]
    
    # Create a simple solution
    logger.info("Creating a simple solution...")
    solution = await assembler.assemble_solution(
        user_request="Create a simple text editor",
        context={
            "device_info": {
                "platform": "linux",
                "memory_gb": 8,
                "cpu_cores": 4,
                "gpu_available": False
            }
        }
    )
    
    logger.info(f"Solution created with ID: {solution.id}")
    logger.info(f"Number of cells: {len(solution.cells)}")
    
    # Interact with the solution
    logger.info("Interact with the solution... (simulate user actions)")
    await asyncio.sleep(2)  # Simulate user interaction
    
    # Release the solution
    logger.info("Releasing solution...")
    await assembler.release_solution(solution.id)
    
    logger.info("Example completed successfully")

async def main():
    """Main function to run the QCC system."""
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Initialize components
    try:
        components = await initialize_system(args.config, args.cell_dir)
        logger.info("QCC system initialized successfully")
        
        # Run example if server is not started
        if args.no_server:
            await run_example(components)
        else:
            # Import here to avoid circular imports
            from server import start_server
            await start_server(components)
    
    except Exception as e:
        logger.error(f"Failed to initialize QCC system: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("QCC system shutdown requested")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)

"""
Node implementation for the Quantum Trail blockchain.

This module provides the BlockchainNode class that handles peer-to-peer
communication, transaction propagation, and block synchronization.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Set, Optional, Tuple
import uuid
import socket

from .blockchain import Blockchain
from .block import Block
from .transaction import Transaction
from .consensus import Consensus
from .crypto import generate_quantum_resistant_keys

logger = logging.getLogger(__name__)


class BlockchainNode:
    """
    Represents a node in the Quantum Trail blockchain network.
    
    This class handles peer-to-peer communication, transaction propagation,
    block mining, and chain synchronization.
    
    Attributes:
        node_id (str): Unique identifier for this node
        blockchain (Blockchain): The blockchain instance
        peers (Set[str]): Set of connected peer addresses
        is_mining (bool): Flag indicating if the node is currently mining
    """
    
    def __init__(
        self,
        blockchain: Optional[Blockchain] = None,
        node_id: Optional[str] = None
    ):
        """
        Initialize a blockchain node.
        
        Args:
            blockchain: Blockchain instance (creates new if None)
            node_id: Node identifier (generated if None)
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.blockchain = blockchain or Blockchain()
        self.peers = set()
        self.is_mining = False
        self.is_running = False
        self.mining_task = None
        
        # Generate keys for this node
        self.private_key, self.public_key = generate_quantum_resistant_keys()
        
        logger.info(f"Initialized blockchain node with ID: {self.node_id}")
    
    async def start(self, host: str = "localhost", port: int = 8000) -> bool:
        """
        Start the blockchain node.
        
        Args:
            host: Host address to bind to
            port: Port to listen on
        
        Returns:
            True if the node started successfully
        """
        self.is_running = True
        
        # Start the mining loop
        self.mining_task = asyncio.create_task(self._mining_loop())
        
        # In a real implementation, this would start a server for P2P communication
        # For simplicity, we'll just log the start and return success
        logger.info(f"Node {self.node_id} started on {host}:{port}")
        return True
    
    async def stop(self) -> bool:
        """
        Stop the blockchain node.
        
        Returns:
            True if the node stopped successfully
        """
        self.is_running = False
        
        # Cancel mining task if active
        if self.mining_task:
            self.mining_task.cancel()
            try:
                await self.mining_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Node {self.node_id} stopped")
        return True
    
    async def _mining_loop(self) -> None:
        """Mining loop that processes pending transactions."""
        try:
            while self.is_running:
                if not self.is_mining and len(self.blockchain.pending_transactions) > 0:
                    # Start mining
                    self.is_mining = True
                    logger.info(f"Starting to mine a new block with {len(self.blockchain.pending_transactions)} transactions")
                    
                    # Mine the block
                    new_block = await self.blockchain.mine_pending_transactions(self.node_id)
                    
                    # If mining was successful, propagate the block to peers
                    if new_block:
                        await self._propagate_block(new_block)
                    
                    self.is_mining = False
                
                # Sleep to avoid busy-waiting
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Mining loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in mining loop: {e}")
    
    async def connect_to_peer(self, peer_address: str) -> bool:
        """
        Connect to a peer node.
        
        Args:
            peer_address: Address of the peer
        
        Returns:
            True if connection was successful
        """
        if peer_address in self.peers:
            logger.info(f"Already connected to peer: {peer_address}")
            return True
        
        # In a real implementation, this would establish a network connection
        # For simplicity, we'll just add the peer to our list
        self.peers.add(peer_address)
        logger.info(f"Connected to peer: {peer_address}")
        
        # Synchronize blockchain with the new peer
        await self._synchronize_with_peer(peer_address)
        
        return True
    
    async def disconnect_from_peer(self, peer_address: str) -> bool:
        """
        Disconnect from a peer node.
        
        Args:
            peer_address: Address of the peer
        
        Returns:
            True if disconnection was successful
        """
        if peer_address not in self.peers:
            logger.info(f"Not connected to peer: {peer_address}")
            return False
        
        # Remove peer from list
        self.peers.remove(peer_address)
        logger.info(f"Disconnected from peer: {peer_address}")
        return True
    
    async def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction and propagate it to peers.
        
        Args:
            transaction: Transaction to add
        
        Returns:
            True if the transaction was added successfully
        """
        # Add to local blockchain
        if not self.blockchain.add_transaction(transaction):
            logger.warning(f"Failed to add transaction: {transaction.id}")
            return False
        
        # Propagate to peers
        await self._propagate_transaction(transaction)
        return True
    
    async def _propagate_transaction(self, transaction: Transaction) -> None:
        """
        Propagate a transaction to all peers.
        
        Args:
            transaction: Transaction to propagate
        """
        # In a real implementation, this would send the transaction to all peers
        # For simplicity, we'll just log the propagation
        logger.info(f"Propagating transaction {transaction.id} to {len(self.peers)} peers")
    
    async def _propagate_block(self, block: Block) -> None:
        """
        Propagate a newly mined block to all peers.
        
        Args:
            block: Block to propagate
        """
        # In a real implementation, this would send the block to all peers
        # For simplicity, we'll just log the propagation
        logger.info(f"Propagating block {block.index} to {len(self.peers)} peers")
    
    async def _synchronize_with_peer(self, peer_address: str) -> bool:
        """
        Synchronize blockchain with a peer.
        
        Args:
            peer_address: Address of the peer
        
        Returns:
            True if synchronization was successful
        """
        # In a real implementation, this would:
        # 1. Request the peer's blockchain
        # 2. Compare with local blockchain
        # 3. Resolve conflicts (longest chain rule)
        
        # For simplicity, we'll just log the synchronization
        logger.info(f"Synchronizing blockchain with peer: {peer_address}")
        return True
    
    async def resolve_conflicts(self) -> bool:
        """
        Resolve conflicts by accepting the longest valid chain from peers.
        
        Returns:
            True if our chain was replaced
        """
        # In a real implementation, this would:
        # 1. Get chains from all peers
        # 2. Find the longest valid chain
        # 3. Replace local chain if a longer valid chain is found
        
        # For simplicity, we'll just log and return False
        logger.info(f"Resolving conflicts with {len(self.peers)} peers")
        return False
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """
        Get information about the blockchain.
        
        Returns:
            Dictionary with blockchain information
        """
        return {
            "node_id": self.node_id,
            "chain_length": len(self.blockchain.chain),
            "pending_transactions": len(self.blockchain.pending_transactions),
            "peers": len(self.peers),
            "is_mining": self.is_mining,
            "is_running": self.is_running,
            "latest_block": self.blockchain.get_latest_block().to_dict() if self.blockchain.chain else None
        }
    
    async def find_similar_patterns(self, capabilities: List[str], max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find patterns similar to the given capabilities.
        
        This is a key function for the Quantum Trail functionality,
        enabling personalization without identification.
        
        Args:
            capabilities: List of required capabilities
            max_results: Maximum number of results to return
        
        Returns:
            List of similar patterns with their performance metrics
        """
        return self.blockchain.find_similar_patterns(capabilities, max_results)
    
    async def record_assembly(
        self,
        quantum_signature: str,
        solution_id: str,
        cell_ids: List[str],
        connection_map: Dict[str, List[str]],
        performance_metrics: Dict[str, Any]
    ) -> bool:
        """
        Record a cell assembly in the blockchain.
        
        Args:
            quantum_signature: Anonymous signature of the user
            solution_id: Identifier for the cell assembly solution
            cell_ids: List of cells in the assembly
            connection_map: How cells are connected
            performance_metrics: Solution performance metrics
        
        Returns:
            True if the assembly was recorded successfully
        """
        # Create a transaction
        transaction = Transaction(
            quantum_signature=quantum_signature,
            solution_id=solution_id,
            cell_ids=cell_ids,
            connection_map=connection_map,
            performance_metrics=performance_metrics
        )
        
        # Add to blockchain
        return await self.add_transaction(transaction)
    
    async def update_assembly_record(
        self,
        quantum_signature: str,
        solution_id: str,
        status: str,
        performance_metrics: Dict[str, Any]
    ) -> bool:
        """
        Update an existing assembly record.
        
        Args:
            quantum_signature: Anonymous signature of the user
            solution_id: Identifier for the cell assembly solution
            status: New status of the solution
            performance_metrics: Updated performance metrics
        
        Returns:
            True if the update was recorded successfully
        """
        # Find existing transactions for this solution
        existing_records = self.blockchain.find_solution_records(solution_id)
        
        if not existing_records:
            logger.warning(f"No existing records found for solution: {solution_id}")
            return False
        
        # Get the latest record
        latest_record = max(existing_records, key=lambda r: r.timestamp)
        
        # Create a new transaction with updated data
        transaction = Transaction(
            quantum_signature=quantum_signature,
            solution_id=solution_id,
            cell_ids=latest_record.cell_ids,
            connection_map=latest_record.connection_map,
            performance_metrics={
                **latest_record.performance_metrics,
                **performance_metrics,
                "status": status,
                "updated_at": time.time()
            }
        )
        
        # Add to blockchain
        return await self.add_transaction(transaction)

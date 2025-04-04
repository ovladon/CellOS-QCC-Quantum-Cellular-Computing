"""
Blockchain Ledger implementation for the QCC Quantum Trail system.

This module provides the core blockchain functionality for storing and
validating quantum trails in a secure, tamper-resistant distributed ledger.
The implementation uses quantum-resistant cryptography to ensure long-term
security even in the presence of quantum computers.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
import json
import hashlib
import os
import aiofiles
from aiofiles import os as aio_os
import base64
from collections import OrderedDict, deque

from qcc.common.exceptions import LedgerError, BlockValidationError, TransactionValidationError
from qcc.quantum_trail.security import SignatureManager

logger = logging.getLogger(__name__)

class Block:
    """
    Represents a block in the blockchain ledger.
    
    A block contains a set of transactions (quantum trail records) and
    is linked to the previous block through a hash, forming a chain.
    
    Attributes:
        index (int): Block position in the chain
        timestamp (float): Block creation time
        transactions (List): List of transactions in the block
        previous_hash (str): Hash of the previous block
        hash (str): Hash of this block
        nonce (int): Value used for proof-of-work
        difficulty (int): Mining difficulty
    """
    
    def __init__(
        self,
        index: int,
        timestamp: float = None,
        transactions: List[Dict[str, Any]] = None,
        previous_hash: str = '',
        nonce: int = 0,
        difficulty: int = 4
    ):
        """
        Initialize a new block.
        
        Args:
            index: Block position in the chain
            timestamp: Block creation time (defaults to current time)
            transactions: List of transactions in the block
            previous_hash: Hash of the previous block
            nonce: Value used for proof-of-work
            difficulty: Mining difficulty
        """
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions or []
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.difficulty = difficulty
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Calculate the hash of this block.
        
        Returns:
            Block hash as a hexadecimal string
        """
        # Create a string representation of the block's contents
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            # Sort transaction fields to ensure consistent hashing
            'transactions': sorted(self.transactions, key=lambda t: t.get('id', '')),
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        
        # Calculate the hash using SHA-256
        hash_object = hashlib.sha256(block_string.encode())
        return hash_object.hexdigest()
    
    def mine_block(self, difficulty: int = None) -> None:
        """
        Mine the block by finding a hash with the required difficulty.
        
        Args:
            difficulty: Mining difficulty (number of leading zeros)
        """
        if difficulty is not None:
            self.difficulty = difficulty
            
        target = '0' * self.difficulty
        
        start_time = time.time()
        iterations = 0
        
        while self.hash[:self.difficulty] != target:
            self.nonce += 1
            iterations += 1
            self.hash = self.calculate_hash()
            
            # Log progress periodically
            if iterations % 100000 == 0:
                elapsed = time.time() - start_time
                logger.debug(f"Mining block {self.index}: {iterations} iterations in {elapsed:.2f}s")
                
        mining_time = time.time() - start_time
        logger.info(f"Block {self.index} mined in {mining_time:.2f}s with {iterations} iterations")
    
    def add_transaction(self, transaction: Dict[str, Any]) -> bool:
        """
        Add a transaction to this block if it's valid.
        
        Args:
            transaction: Transaction to add
            
        Returns:
            True if transaction was added, False otherwise
        """
        # Ensure transaction has the required fields
        required_fields = ['id', 'timestamp', 'signature', 'data']
        if not all(field in transaction for field in required_fields):
            logger.warning(f"Transaction missing required fields: {transaction.get('id', 'unknown')}")
            return False
        
        self.transactions.append(transaction)
        
        # Update the hash
        self.hash = self.calculate_hash()
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the block to a dictionary.
        
        Returns:
            Dictionary representation of the block
        """
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Block':
        """
        Create a block from a dictionary.
        
        Args:
            data: Dictionary representation of a block
            
        Returns:
            Block object
        """
        block = Block(
            index=data['index'],
            timestamp=data['timestamp'],
            transactions=data['transactions'],
            previous_hash=data['previous_hash'],
            nonce=data['nonce'],
            difficulty=data['difficulty']
        )
        
        # Set hash directly instead of recalculating
        block.hash = data['hash']
        
        return block


class BlockchainLedger:
    """
    Implements a blockchain ledger for quantum trail records.
    
    The ledger stores quantum trail records in a blockchain structure,
    ensuring that records cannot be altered once added to the chain.
    
    Attributes:
        chain (List[Block]): The blockchain
        pending_transactions (List): Transactions waiting to be mined
        nodes (Set[str]): Set of connected nodes for consensus
        signature_manager (SignatureManager): Manager for cryptographic operations
        config (Dict): Ledger configuration
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the blockchain ledger.
        
        Args:
            config: Ledger configuration
        """
        self.config = config or {}
        self.chain = []
        self.pending_transactions = []
        self.nodes = set()
        
        # Create a signature manager for cryptographic operations
        self.signature_manager = SignatureManager(
            self.config.get("signature", {})
        )
        
        # Set up storage
        self.storage_path = self.config.get("storage_path", "./data/blockchain")
        
        # Initialize mining lock
        self.mining_lock = asyncio.Lock()
        
        # Set up blockchain parameters
        self.difficulty = self.config.get("difficulty", 4)
        self.block_capacity = self.config.get("block_capacity", 100)
        self.block_time_target_seconds = self.config.get("block_time_target_seconds", 60)
        self.difficulty_adjustment_interval = self.config.get("difficulty_adjustment_interval", 10)
        
        # Set up metrics
        self.start_time = datetime.now()
        self.transaction_count = 0
        self.last_difficulty_adjustment = 0
        self.block_times = deque(maxlen=100)
        
        logger.info("Blockchain ledger initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the blockchain ledger.
        
        Creates the genesis block if the chain is empty.
        """
        # Ensure storage directory exists
        await self._ensure_storage_path()
        
        # Try to load existing chain
        loaded = await self._load_chain()
        
        if not loaded or not self.chain:
            # Create genesis block
            logger.info("Creating genesis block")
            genesis_block = Block(0)
            genesis_block.timestamp = time.time()
            genesis_block.hash = genesis_block.calculate_hash()
            self.chain = [genesis_block]
            
            # Save genesis block
            await self._save_chain()
        
        logger.info(f"Blockchain initialized with {len(self.chain)} blocks")
        
        # Start background tasks
        if self.config.get("auto_mining", True):
            self.mining_task = asyncio.create_task(self._auto_mining_task())
    
    async def _ensure_storage_path(self) -> None:
        """Ensure the storage directory exists."""
        try:
            if not os.path.exists(self.storage_path):
                os.makedirs(self.storage_path, exist_ok=True)
                logger.info(f"Created storage directory: {self.storage_path}")
        
        except Exception as e:
            logger.error(f"Failed to create storage directory: {e}")
            raise LedgerError(f"Failed to initialize ledger storage: {e}")
    
    async def _load_chain(self) -> bool:
        """
        Load the blockchain from storage.
        
        Returns:
            True if chain was loaded successfully, False otherwise
        """
        chain_path = os.path.join(self.storage_path, "chain.json")
        
        try:
            if os.path.exists(chain_path):
                async with aiofiles.open(chain_path, 'r') as f:
                    chain_data = json.loads(await f.read())
                
                # Create blocks from the data
                self.chain = [Block.from_dict(block_data) for block_data in chain_data]
                
                # Validate the loaded chain
                if not self._is_chain_valid():
                    logger.warning("Loaded chain is invalid, creating new chain")
                    self.chain = []
                    return False
                
                logger.info(f"Loaded chain with {len(self.chain)} blocks")
                return True
            else:
                logger.info("No existing chain found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load chain: {e}", exc_info=True)
            return False
    
    async def _save_chain(self) -> None:
        """Save the blockchain to storage."""
        chain_path = os.path.join(self.storage_path, "chain.json")
        
        try:
            # Convert chain to JSON-serializable format
            chain_data = [block.to_dict() for block in self.chain]
            
            # Write to temporary file first
            temp_path = f"{chain_path}.tmp"
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write(json.dumps(chain_data, indent=2))
            
            # Rename temporary file to actual chain file (atomic operation)
            os.replace(temp_path, chain_path)
            
            logger.debug(f"Chain saved with {len(self.chain)} blocks")
            
        except Exception as e:
            logger.error(f"Failed to save chain: {e}", exc_info=True)
            raise LedgerError(f"Failed to save blockchain: {e}")
    
    def _is_chain_valid(self) -> bool:
        """
        Validate the blockchain.
        
        Returns:
            True if the chain is valid, False otherwise
        """
        # Check for empty chain
        if not self.chain:
            return True
        
        # Iterate through the blocks
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            # Check hash integrity
            if current.previous_hash != previous.hash:
                logger.error(f"Block {current.index}: previous_hash doesn't match Block {previous.index}'s hash")
                return False
            
            # Check if hash is correct
            if current.hash != current.calculate_hash():
                logger.error(f"Block {current.index}: hash doesn't match calculated hash")
                return False
            
            # Check proof-of-work
            if current.hash[:current.difficulty] != '0' * current.difficulty:
                logger.error(f"Block {current.index}: hash doesn't meet difficulty requirement")
                return False
        
        return True
    
    async def _auto_mining_task(self) -> None:
        """Background task for automatic mining."""
        while True:
            try:
                # Check if we have enough transactions to mine a block
                if len(self.pending_transactions) >= self.block_capacity:
                    logger.info(f"Mining block with {len(self.pending_transactions)} transactions")
                    await self.mine_pending_transactions()
                
                # Check if we have transactions waiting for too long
                elif self.pending_transactions:
                    # Get oldest pending transaction
                    oldest_timestamp = min(tx['timestamp'] for tx in self.pending_transactions)
                    current_time = time.time()
                    
                    max_wait_time = self.config.get("max_transaction_wait_seconds", 300)
                    
                    if current_time - oldest_timestamp > max_wait_time:
                        logger.info(f"Mining block with {len(self.pending_transactions)} transactions (wait time exceeded)")
                        await self.mine_pending_transactions()
                
                # Sleep for a bit
                await asyncio.sleep(self.config.get("mining_check_interval_seconds", 5))
                
            except asyncio.CancelledError:
                logger.info("Auto mining task cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in auto mining task: {e}", exc_info=True)
                await asyncio.sleep(30)  # Sleep longer on error
    
    async def add_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """
        Add a new transaction to the pending transactions.
        
        Args:
            transaction_data: Transaction data
            
        Returns:
            Transaction ID
            
        Raises:
            TransactionValidationError: If the transaction is invalid
        """
        try:
            # Create transaction
            transaction = {
                'id': str(uuid.uuid4()),
                'timestamp': time.time(),
                'data': transaction_data,
                'signature': None
            }
            
            # Generate signature
            signature = await self.signature_manager.sign_transaction(transaction)
            transaction['signature'] = signature
            
            # Validate transaction
            valid, reason = await self.signature_manager.verify_transaction(transaction)
            if not valid:
                raise TransactionValidationError(f"Invalid transaction: {reason}")
            
            # Add to pending transactions
            self.pending_transactions.append(transaction)
            self.transaction_count += 1
            
            logger.debug(f"Added transaction {transaction['id']}")
            
            return transaction['id']
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}", exc_info=True)
            if isinstance(e, TransactionValidationError):
                raise
            raise TransactionValidationError(f"Failed to add transaction: {e}")
    
    async def mine_pending_transactions(self) -> Optional[Block]:
        """
        Mine pending transactions into a new block.
        
        Returns:
            The newly mined block or None if no transactions to mine
            
        Raises:
            LedgerError: If mining fails
        """
        # Check if we have pending transactions
        if not self.pending_transactions:
            logger.debug("No pending transactions to mine")
            return None
        
        # Acquire mining lock to prevent concurrent mining
        async with self.mining_lock:
            try:
                # Get the latest block
                latest_block = self.chain[-1]
                
                # Create a new block
                new_block = Block(
                    index=latest_block.index + 1,
                    previous_hash=latest_block.hash,
                    transactions=self.pending_transactions[:self.block_capacity],
                    difficulty=self.difficulty
                )
                
                # Mine the block
                start_time = time.time()
                new_block.mine_block()
                mining_time = time.time() - start_time
                
                # Add block to the chain
                self.chain.append(new_block)
                
                # Track block time
                self.block_times.append(mining_time)
                
                # Remove mined transactions from pending list
                self.pending_transactions = self.pending_transactions[len(new_block.transactions):]
                
                # Save the updated chain
                await self._save_chain()
                
                # Adjust difficulty if needed
                await self._adjust_difficulty()
                
                logger.info(f"Mined block {new_block.index} with {len(new_block.transactions)} transactions")
                
                return new_block
                
            except Exception as e:
                logger.error(f"Error mining block: {e}", exc_info=True)
                raise LedgerError(f"Failed to mine block: {e}")
    
    async def _adjust_difficulty(self) -> None:
        """Adjust mining difficulty based on recent block times."""
        # Check if we need to adjust difficulty
        if len(self.chain) - self.last_difficulty_adjustment < self.difficulty_adjustment_interval:
            return
        
        # Get average block time
        if not self.block_times:
            return
            
        avg_block_time = sum(self.block_times) / len(self.block_times)
        
        # Adjust difficulty based on average block time
        if avg_block_time < self.block_time_target_seconds * 0.5:
            # Blocks are being mined too quickly, increase difficulty
            self.difficulty += 1
            logger.info(f"Increased mining difficulty to {self.difficulty}")
        elif avg_block_time > self.block_time_target_seconds * 2:
            # Blocks are being mined too slowly, decrease difficulty
            if self.difficulty > 1:
                self.difficulty -= 1
                logger.info(f"Decreased mining difficulty to {self.difficulty}")
        
        # Update last adjustment block
        self.last_difficulty_adjustment = len(self.chain)
    
    async def add_node(self, address: str) -> None:
        """
        Add a new node to the network.
        
        Args:
            address: Address of the node to add
        """
        self.nodes.add(address)
        logger.info(f"Added node: {address}")
    
    async def consensus(self) -> bool:
        """
        Resolve conflicts by replacing our chain with the longest valid chain.
        
        Returns:
            True if our chain was replaced, False otherwise
        """
        if not self.nodes:
            logger.debug("No nodes in network, skipping consensus")
            return False
            
        neighbors = self.nodes
        new_chain = None
        
        # Look for chains longer than ours
        max_length = len(self.chain)
        
        # Check each node in the network
        for node in neighbors:
            try:
                # Get the chain from the node
                chain_data = await self._get_chain_from_node(node)
                
                # Convert to Block objects
                chain = [Block.from_dict(block_data) for block_data in chain_data]
                
                # Check if the chain is valid and longer than ours
                if len(chain) > max_length and self._is_chain_valid(chain):
                    max_length = len(chain)
                    new_chain = chain
                    
            except Exception as e:
                logger.warning(f"Error getting chain from node {node}: {e}")
        
        # Replace our chain if we found a longer valid chain
        if new_chain:
            self.chain = new_chain
            await self._save_chain()
            logger.info(f"Chain replaced with longer chain ({len(new_chain)} blocks)")
            return True
            
        logger.debug("Our chain is authoritative")
        return False
    
    async def _get_chain_from_node(self, node_address: str) -> List[Dict[str, Any]]:
        """
        Get the blockchain from a node.
        
        Args:
            node_address: Address of the node
            
        Returns:
            The blockchain data
            
        Raises:
            Exception: If getting the chain fails
        """
        # In a real implementation, this would make an HTTP request to the node
        # For this example, we'll simulate it
        
        raise NotImplementedError("Getting chain from nodes not implemented")
    
    def _is_chain_valid(self, chain: List[Block] = None) -> bool:
        """
        Validate a blockchain.
        
        Args:
            chain: The blockchain to validate (uses self.chain if None)
            
        Returns:
            True if the chain is valid, False otherwise
        """
        chain = chain or self.chain
        
        # Check for empty chain
        if not chain:
            return True
        
        # Iterate through the blocks
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]
            
            # Check hash integrity
            if current.previous_hash != previous.hash:
                logger.error(f"Block {current.index}: previous_hash doesn't match Block {previous.index}'s hash")
                return False
            
            # Check if hash is correct
            if current.hash != current.calculate_hash():
                logger.error(f"Block {current.index}: hash doesn't match calculated hash")
                return False
            
            # Check proof-of-work
            if current.hash[:current.difficulty] != '0' * current.difficulty:
                logger.error(f"Block {current.index}: hash doesn't meet difficulty requirement")
                return False
        
        return True
    
    async def get_block_by_index(self, index: int) -> Optional[Block]:
        """
        Get a block by its index.
        
        Args:
            index: Block index
            
        Returns:
            Block or None if not found
        """
        if 0 <= index < len(self.chain):
            return self.chain[index]
        
        return None
    
    async def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Get a block by its hash.
        
        Args:
            block_hash: Block hash
            
        Returns:
            Block or None if not found
        """
        for block in self.chain:
            if block.hash == block_hash:
                return block
        
        return None
    
    async def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a transaction by its ID.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Transaction data or None if not found
        """
        # Check pending transactions
        for tx in self.pending_transactions:
            if tx.get('id') == transaction_id:
                return tx
        
        # Check mined transactions
        for block in reversed(self.chain):  # Start from most recent blocks
            for tx in block.transactions:
                if tx.get('id') == transaction_id:
                    return tx
        
        return None
    
    async def search_transactions(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for transactions that match the query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching transactions
        """
        results = []
        
        # Function to check if a transaction matches the query
        def matches(tx, query):
            for key, value in query.items():
                # Handle nested fields with dot notation
                if '.' in key:
                    parts = key.split('.')
                    tx_value = tx
                    for part in parts:
                        if isinstance(tx_value, dict) and part in tx_value:
                            tx_value = tx_value[part]
                        else:
                            return False
                    
                    if tx_value != value:
                        return False
                
                # Handle direct fields
                elif key not in tx or tx[key] != value:
                    return False
            
            return True
        
        # Search in pending transactions
        for tx in self.pending_transactions:
            if matches(tx, query):
                results.append(tx)
        
        # Search in mined transactions
        for block in reversed(self.chain):  # Start from most recent blocks
            for tx in block.transactions:
                if matches(tx, query):
                    results.append(tx)
                    
                    # Limit results
                    if len(results) >= self.config.get("max_search_results", 100):
                        return results
        
        return results
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the blockchain.
        
        Returns:
            Status information
        """
        # Calculate uptime
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate average block time
        avg_block_time = 0
        if self.block_times:
            avg_block_time = sum(self.block_times) / len(self.block_times)
        
        # Calculate transactions per block
        tx_per_block = 0
        if len(self.chain) > 1:  # Exclude genesis block
            total_tx = sum(len(block.transactions) for block in self.chain[1:])
            tx_per_block = total_tx / (len(self.chain) - 1) if len(self.chain) > 1 else 0
        
        return {
            "chain_length": len(self.chain),
            "pending_transactions": len(self.pending_transactions),
            "total_transactions": self.transaction_count,
            "difficulty": self.difficulty,
            "avg_block_time": avg_block_time,
            "tx_per_block": tx_per_block,
            "connected_nodes": len(self.nodes),
            "uptime_seconds": uptime_seconds,
            "is_valid": self._is_chain_valid()
        }
    
    async def backup_ledger(self, backup_path: str = None) -> str:
        """
        Create a backup of the ledger.
        
        Args:
            backup_path: Path to store the backup
            
        Returns:
            Path to the backup
        """
        if not backup_path:
            backup_path = f"{self.storage_path}_backup_{int(time.time())}"
        
        try:
            # Ensure backup directory exists
            os.makedirs(backup_path, exist_ok=True)
            
            # Save chain to backup path
            chain_data = [block.to_dict() for block in self.chain]
            
            backup_file = os.path.join(backup_path, "chain.json")
            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(json.dumps(chain_data, indent=2))
            
            # Save pending transactions
            if self.pending_transactions:
                pending_file = os.path.join(backup_path, "pending_transactions.json")
                async with aiofiles.open(pending_file, 'w') as f:
                    await f.write(json.dumps(self.pending_transactions, indent=2))
            
            logger.info(f"Blockchain ledger backup created at {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating ledger backup: {e}", exc_info=True)
            raise LedgerError(f"Failed to create ledger backup: {e}")

# Convenience function to create and configure a blockchain ledger
async def create_blockchain_ledger(config_path: str = None) -> BlockchainLedger:
    """
    Create and configure a Blockchain Ledger instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured BlockchainLedger instance
    """
    # Load configuration
    config = {}
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            logger.warning("Using default configuration")
    
    # Create blockchain ledger
    ledger = BlockchainLedger(config)
    
    # Initialize
    await ledger.initialize()
    
    return ledger

"""
Core blockchain implementation for the Quantum Trail.

This module provides the main Blockchain class that manages the
chain of blocks, adds new transactions, and maintains consensus.
"""

import time
import json
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import logging

from .block import Block
from .transaction import Transaction
from .consensus import Consensus

logger = logging.getLogger(__name__)


class Blockchain:
    """
    Core blockchain implementation for the Quantum Trail.
    
    This class manages the chain of blocks, adds new transactions,
    and maintains consensus across the network.
    
    Attributes:
        chain (List[Block]): The blockchain
        pending_transactions (List[Transaction]): Transactions waiting to be added to a block
        consensus_algorithm (Consensus): The consensus algorithm for block validation
        difficulty (int): Mining difficulty for proof-of-work
    """
    
    def __init__(
        self,
        consensus_algorithm: Optional[Consensus] = None,
        difficulty: int = 4,
        existing_chain: Optional[List[Block]] = None
    ):
        """
        Initialize a new blockchain.
        
        Args:
            consensus_algorithm: Consensus algorithm (defaults to PoW)
            difficulty: Mining difficulty for PoW
            existing_chain: Existing blockchain to import
        """
        self.pending_transactions = []
        self.consensus_algorithm = consensus_algorithm or Consensus(difficulty=difficulty)
        self.difficulty = difficulty
        
        # Initialize the chain
        if existing_chain:
            self.chain = existing_chain
        else:
            self.chain = [self._create_genesis_block()]
    
    def _create_genesis_block(self) -> Block:
        """
        Create the genesis block.
        
        Returns:
            Genesis block
        """
        genesis_transaction = Transaction(
            quantum_signature="genesis",
            solution_id="genesis",
            cell_ids=["genesis"],
            connection_map={},
            performance_metrics={"genesis": True}
        )
        
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=[genesis_transaction],
            previous_hash="0"
        )
        
        return genesis_block
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a new transaction to pending transactions.
        
        Args:
            transaction: Transaction to add
        
        Returns:
            True if the transaction was added successfully
        """
        if not transaction.is_valid():
            logger.warning(f"Invalid transaction: {transaction.id}")
            return False
        
        self.pending_transactions.append(transaction)
        logger.info(f"Added transaction {transaction.id} to pending pool")
        return True
    
    async def mine_pending_transactions(self, miner_reward_address: str) -> Optional[Block]:
        """
        Mine pending transactions into a new block.
        
        Args:
            miner_reward_address: Address to receive mining reward
        
        Returns:
            The newly mined block, or None if mining failed
        """
        if not self.pending_transactions:
            logger.info("No pending transactions to mine")
            return None
        
        # Create a reward transaction
        reward_transaction = Transaction(
            quantum_signature=miner_reward_address,
            solution_id="mining_reward",
            cell_ids=[],
            connection_map={},
            performance_metrics={"reward": True}
        )
        
        # Get a copy of pending transactions and add reward
        transactions_to_mine = self.pending_transactions.copy()
        transactions_to_mine.append(reward_transaction)
        
        # Create a new block
        new_block = Block(
            index=len(self.chain),
            transactions=transactions_to_mine,
            previous_hash=self.chain[-1].hash
        )
        
        # Run the consensus algorithm
        success = await self.consensus_algorithm.run_consensus(new_block)
        
        if success:
            # Add the new block to the chain
            self.chain.append(new_block)
            
            # Clear the pending transactions
            self.pending_transactions = []
            
            logger.info(f"Mined new block {new_block.index} with {len(new_block.transactions)} transactions")
            return new_block
        
        logger.warning("Failed to mine new block")
        return None
    
    def is_chain_valid(self) -> bool:
        """
        Validate the entire blockchain.
        
        Returns:
            True if the blockchain is valid
        """
        # Check each block in the chain
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Validate the block's hash
            if current_block.hash != current_block.calculate_hash():
                logger.error(f"Block {i} has invalid hash")
                return False
            
            # Validate the link to the previous block
            if current_block.previous_hash != previous_block.hash:
                logger.error(f"Block {i} has invalid previous hash")
                return False
            
            # Validate all transactions in the block
            for transaction in current_block.transactions:
                if not transaction.is_valid():
                    logger.error(f"Block {i} contains invalid transaction")
                    return False
        
        return True
    
    def get_latest_block(self) -> Block:
        """
        Get the latest block in the chain.
        
        Returns:
            Latest block
        """
        return self.chain[-1]
    
    def find_solution_records(self, solution_id: str) -> List[Transaction]:
        """
        Find all transactions related to a specific solution.
        
        Args:
            solution_id: Solution ID to search for
        
        Returns:
            List of transactions for the solution
        """
        records = []
        
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.solution_id == solution_id:
                    records.append(transaction)
        
        return records
    
    def find_similar_patterns(self, capabilities: List[str], max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find patterns similar to the given capabilities.
        
        Args:
            capabilities: List of required capabilities
            max_results: Maximum number of results to return
        
        Returns:
            List of similar patterns with their performance metrics
        """
        patterns = []
        
        # Search through all transactions
        for block in self.chain:
            for transaction in block.transactions:
                # Skip reward transactions
                if transaction.solution_id == "mining_reward":
                    continue
                
                # Check if this transaction has similar capabilities
                # by comparing the cell_ids (simplified approach)
                match_score = 0
                for cell_id in transaction.cell_ids:
                    # In a real implementation, we would look up the cell's capability
                    # For this example, we'll use a simplified approach
                    cell_capability = cell_id.split("_")[0] if "_" in cell_id else cell_id
                    if cell_capability in capabilities:
                        match_score += 1
                
                similarity = match_score / max(len(capabilities), len(transaction.cell_ids))
                
                if similarity > 0.5:  # Arbitrary threshold
                    patterns.append({
                        "solution_id": transaction.solution_id,
                        "cell_ids": transaction.cell_ids,
                        "connection_map": transaction.connection_map,
                        "performance_metrics": transaction.performance_metrics,
                        "similarity_score": similarity
                    })
        
        # Sort by similarity score and limit results
        patterns.sort(key=lambda p: p["similarity_score"], reverse=True)
        return patterns[:max_results]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the blockchain to a dictionary.
        
        Returns:
            Dictionary representation of the blockchain
        """
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
            "difficulty": self.difficulty
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Blockchain':
        """
        Create a blockchain from a dictionary.
        
        Args:
            data: Dictionary representation of a blockchain
        
        Returns:
            Blockchain object
        """
        chain = [Block.from_dict(block_data) for block_data in data.get("chain", [])]
        pending_transactions = [Transaction.from_dict(tx_data) for tx_data in data.get("pending_transactions", [])]
        difficulty = data.get("difficulty", 4)
        
        blockchain = cls(
            difficulty=difficulty,
            existing_chain=chain
        )
        
        blockchain.pending_transactions = pending_transactions
        return blockchain
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save the blockchain to a file.
        
        Args:
            filepath: Path to the file
        
        Returns:
            True if the blockchain was saved successfully
        """
        try:
            with open(filepath, 'w') as file:
                json.dump(self.to_dict(), file, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save blockchain: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['Blockchain']:
        """
        Load a blockchain from a file.
        
        Args:
            filepath: Path to the file
        
        Returns:
            Blockchain object, or None if loading failed
        """
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load blockchain: {e}")
            return None

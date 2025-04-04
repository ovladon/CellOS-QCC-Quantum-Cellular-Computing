"""
Block definition for the Quantum Trail blockchain.

This module defines the Block class, which represents a single block in the
blockchain, containing a set of transactions and metadata.
"""

import time
import json
from typing import List, Dict, Any, Optional
import hashlib

from .transaction import Transaction
from .crypto import hash_data


class Block:
    """
    Represents a block in the Quantum Trail blockchain.
    
    Each block contains a set of transactions, metadata, and links to
    the previous block through a cryptographic hash.
    
    Attributes:
        index (int): Block index in the chain
        timestamp (float): Unix timestamp of block creation
        transactions (List[Transaction]): List of transactions in the block
        previous_hash (str): Hash of the previous block
        nonce (int): Nonce used for consensus algorithm
        hash (str): Hash of this block
    """
    
    def __init__(
        self,
        index: int,
        timestamp: Optional[float] = None,
        transactions: Optional[List[Transaction]] = None,
        previous_hash: str = "",
        nonce: int = 0
    ):
        """
        Initialize a new block.
        
        Args:
            index: Block index in the chain
            timestamp: Unix timestamp (defaults to current time)
            transactions: List of transactions
            previous_hash: Hash of the previous block
            nonce: Nonce used for consensus algorithm
        """
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions or []
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Calculate the hash of this block.
        
        Returns:
            Cryptographic hash of the block
        """
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        
        return hash_data(block_data)
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction to the block.
        
        Args:
            transaction: Transaction to add
        
        Returns:
            True if the transaction was added successfully
        """
        if not transaction.is_valid():
            return False
        
        self.transactions.append(transaction)
        self.hash = self.calculate_hash()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the block to a dictionary.
        
        Returns:
            Dictionary representation of the block
        """
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """
        Create a block from a dictionary.
        
        Args:
            data: Dictionary representation of a block
        
        Returns:
            Block object
        """
        transactions = [Transaction.from_dict(tx) for tx in data.get("transactions", [])]
        
        block = cls(
            index=data.get("index", 0),
            timestamp=data.get("timestamp"),
            transactions=transactions,
            previous_hash=data.get("previous_hash", ""),
            nonce=data.get("nonce", 0)
        )
        
        # Set the hash directly if provided
        if "hash" in data:
            block.hash = data["hash"]
        
        return block
    
    def is_valid(self) -> bool:
        """
        Validate the block.
        
        Returns:
            True if the block is valid
        """
        # Verify all transactions
        for transaction in self.transactions:
            if not transaction.is_valid():
                return False
        
        # Check that the hash is correct
        if self.hash != self.calculate_hash():
            return False
        
        return True

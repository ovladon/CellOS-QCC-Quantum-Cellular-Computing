"""
Differential privacy mechanisms for the QCC Quantum Trail.

This module provides techniques to add controlled noise to data, enabling
statistical analysis while protecting individual privacy.
"""

import math
import random
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Union, Callable

logger = logging.getLogger(__name__)

@dataclass
class PrivacyBudget:
    """Represents a privacy budget for differential privacy."""
    
    # Epsilon controls the privacy-utility tradeoff
    # Lower epsilon = more privacy, less utility
    epsilon: float = 1.0
    
    # Delta is the probability of information leakage
    # Lower delta = more privacy
    delta: float = 1e-5
    
    # Maximum queries allowed under this budget
    max_queries: int = 100
    
    # Current query count
    query_count: int = 0
    
    # Budget expires after this time (timestamp)
    expiration: Optional[float] = None
    
    def __post_init__(self):
        """Initialize expiration if not set."""
        if self.expiration is None:
            # Default expiration: 24 hours from now
            self.expiration = time.time() + 86400
    
    def consume(self, epsilon_cost: float = 1.0) -> bool:
        """
        Consume some of the privacy budget.
        
        Args:
            epsilon_cost: Amount of epsilon to consume
            
        Returns:
            True if budget was successfully consumed, False if exceeded
        """
        # Check if budget has expired
        if time.time() > self.expiration:
            return False
        
        # Check if max queries exceeded
        if self.query_count >= self.max_queries:
            return False
        
        # Check if would exceed epsilon
        if epsilon_cost > self.epsilon:
            return False
        
        # Consume budget
        self.epsilon -= epsilon_cost
        self.query_count += 1
        
        return True
    
    def remaining_percentage(self) -> float:
        """
        Calculate remaining percentage of privacy budget.
        
        Returns:
            Percentage of budget remaining (0-100)
        """
        # Time component
        total_time = self.expiration - (self.expiration - 86400)  # 24 hours
        elapsed_time = time.time() - (self.expiration - 86400)
        time_remaining = max(0, 1 - (elapsed_time / total_time))
        
        # Query component
        query_remaining = max(0, 1 - (self.query_count / self.max_queries))
        
        # Epsilon component (assuming initial epsilon was 1.0)
        epsilon_remaining = self.epsilon
        
        # Combine factors (weighted average)
        return (time_remaining * 0.3 + query_remaining * 0.3 + epsilon_remaining * 0.4) * 100


class DifferentialPrivacy:
    """
    Implements differential privacy mechanisms.
    
    This class provides methods to add controlled noise to data, enabling
    statistical analysis while protecting individual privacy.
    """
    
    def __init__(self, default_budget: PrivacyBudget = None):
        """
        Initialize the differential privacy module.
        
        Args:
            default_budget: Default privacy budget
        """
        self.default_budget = default_budget or PrivacyBudget()
        self.query_history = []
        
    def add_laplace_noise(self, value: float, sensitivity: float, 
                         budget: PrivacyBudget = None) -> float:
        """
        Add Laplace noise to a numeric value.
        
        Args:
            value: Original value
            sensitivity: Sensitivity of the query
            budget: Privacy budget (uses default if not provided)
            
        Returns:
            Value with noise added
        """
        budget = budget or self.default_budget
        
        # Calculate scale based on sensitivity and epsilon
        scale = sensitivity / budget.epsilon
        
        # Consume privacy budget
        if not budget.consume(1.0):
            logger.warning("Privacy budget exceeded, returning None")
            return None
        
        # Generate Laplace noise
        noise = self._sample_laplace(0, scale)
        
        # Add noise to value
        noisy_value = value + noise
        
        # Log query
        self._log_query("laplace", value, noisy_value, sensitivity, budget.epsilon)
        
        return noisy_value
    
    def add_gaussian_noise(self, value: float, sensitivity: float, 
                          budget: PrivacyBudget = None) -> float:
        """
        Add Gaussian noise to a numeric value.
        
        Args:
            value: Original value
            sensitivity: Sensitivity of the query
            budget: Privacy budget (uses default if not provided)
            
        Returns:
            Value with noise added
        """
        budget = budget or self.default_budget
        
        # Calculate sigma based on sensitivity, epsilon, and delta
        sigma = (sensitivity / budget.epsilon) * math.sqrt(2 * math.log(1.25 / budget.delta))
        
        # Consume privacy budget
        if not budget.consume(1.0):
            logger.warning("Privacy budget exceeded, returning None")
            return None
        
        # Generate Gaussian noise
        noise = random.gauss(0, sigma)
        
        # Add noise to value
        noisy_value = value + noise
        
        # Log query
        self._log_query("gaussian", value, noisy_value, sensitivity, budget.epsilon)
        
        return noisy_value
    
    def privatize_histogram(self, counts: Dict[str, int], sensitivity: int = 1, 
                           budget: PrivacyBudget = None) -> Dict[str, float]:
        """
        Apply differential privacy to a histogram.
        
        Args:
            counts: Count dictionary
            sensitivity: Sensitivity of the histogram
            budget: Privacy budget (uses default if not provided)
            
        Returns:
            Privatized histogram
        """
        budget = budget or self.default_budget
        
        # Check if we have enough budget for all histogram bins
        # Each bin consumes a fraction of epsilon
        epsilon_per_bin = budget.epsilon / len(counts)
        
        # Consume privacy budget
        if not budget.consume(budget.epsilon):
            logger.warning("Privacy budget exceeded, returning None")
            return None
        
        # Add noise to each count
        privatized = {}
        for key, count in counts.items():
            # Calculate scale based on sensitivity and epsilon per bin
            scale = sensitivity / epsilon_per_bin
            
            # Generate Laplace noise
            noise = self._sample_laplace(0, scale)
            
            # Add noise and ensure result is non-negative
            privatized[key] = max(0, count + noise)
        
        # Log query
        self._log_query("histogram", counts, privatized, sensitivity, budget.epsilon)
        
        return privatized
    
    def privatize_quantile(self, data: List[float], quantile: float, 
                          sensitivity: float = 1.0, budget: PrivacyBudget = None) -> float:
        """
        Apply differential privacy to a quantile computation.
        
        Args:
            data: Data points
            quantile: Quantile to compute (0-1)
            sensitivity: Sensitivity of the quantile
            budget: Privacy budget (uses default if not provided)
            
        Returns:
            Privatized quantile
        """
        budget = budget or self.default_budget
        
        # Calculate the true quantile
        sorted_data = sorted(data)
        index = int(quantile * len(sorted_data))
        true_quantile = sorted_data[index]
        
        # Calculate scale based on sensitivity and epsilon
        scale = sensitivity / budget.epsilon
        
        # Consume privacy budget
        if not budget.consume(1.0):
            logger.warning("Privacy budget exceeded, returning None")
            return None
        
        # Generate noise and add to the quantile
        noise = self._sample_laplace(0, scale)
        private_quantile = true_quantile + noise
        
        # Log query
        self._log_query("quantile", true_quantile, private_quantile, sensitivity, budget.epsilon)
        
        return private_quantile
    
    def privatize_mean(self, data: List[float], sensitivity: float, 
                      budget: PrivacyBudget = None) -> float:
        """
        Apply differential privacy to a mean computation.
        
        Args:
            data: Data points
            sensitivity: Sensitivity of the mean
            budget: Privacy budget (uses default if not provided)
            
        Returns:
            Privatized mean
        """
        budget = budget or self.default_budget
        
        # Calculate the true mean
        true_mean = sum(data) / len(data)
        
        # Calculate scale based on sensitivity and epsilon
        # For mean, sensitivity is reduced by the number of data points
        scale = (sensitivity / len(data)) / budget.epsilon
        
        # Consume privacy budget
        if not budget.consume(1.0):
            logger.warning("Privacy budget exceeded, returning None")
            return None
        
        # Generate noise and add to the mean
        noise = self._sample_laplace(0, scale)
        private_mean = true_mean + noise
        
        # Log query
        self._log_query("mean", true_mean, private_mean, sensitivity, budget.epsilon)
        
        return private_mean
    
    def _sample_laplace(self, mu: float, scale: float) -> float:
        """
        Sample from a Laplace distribution.
        
        Args:
            mu: Mean
            scale: Scale parameter
            
        Returns:
            Random sample
        """
        # Generate uniform random value in (0, 1)
        u = random.random()
        while u == 0 or u == 1:
            u = random.random()
        
        # Transform to Laplace
        if u < 0.5:
            return mu + scale * math.log(2 * u)
        else:
            return mu - scale * math.log(2 * (1 - u))
    
    def _log_query(self, mechanism: str, original: Any, privatized: Any, 
                  sensitivity: float, epsilon: float) -> None:
        """
        Log a privacy query for auditing.
        
        Args:
            mechanism: Privacy mechanism used
            original: Original value
            privatized: Privatized value
            sensitivity: Query sensitivity
            epsilon: Epsilon value used
        """
        query_info = {
            "timestamp": time.time(),
            "mechanism": mechanism,
            "sensitivity": sensitivity,
            "epsilon": epsilon,
            # Don't log actual values, just basic info for auditing
            "type": str(type(original)),
            "has_original": original is not None,
            "has_privatized": privatized is not None
        }
        
        self.query_history.append(query_info)
        
        # Trim history if it gets too long
        if len(self.query_history) > 1000:
            self.query_history = self.query_history[-1000:]
    
    def get_query_stats(self) -> Dict[str, Any]:
        """
        Get statistics about privacy queries.
        
        Returns:
            Query statistics
        """
        if not self.query_history:
            return {
                "count": 0,
                "mechanisms": {}
            }
        
        # Count queries by mechanism
        mechanism_counts = {}
        for query in self.query_history:
            mechanism = query["mechanism"]
            mechanism_counts[mechanism] = mechanism_counts.get(mechanism, 0) + 1
        
        # Calculate average epsilon
        avg_epsilon = sum(q["epsilon"] for q in self.query_history) / len(self.query_history)
        
        # Get time range
        start_time = min(q["timestamp"] for q in self.query_history)
        end_time = max(q["timestamp"] for q in self.query_history)
        
        return {
            "count": len(self.query_history),
            "mechanisms": mechanism_counts,
            "avg_epsilon": avg_epsilon,
            "time_range": {
                "start": start_time,
                "end": end_time,
                "duration_seconds": end_time - start_time
            }
        }

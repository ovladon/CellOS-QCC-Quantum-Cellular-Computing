"""
Privacy management system for the QCC Quantum Trail.

This module provides a unified interface for managing privacy in the Quantum Trail,
combining anonymization, zero-knowledge proofs, and differential privacy.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable

from .anonymizer import Anonymizer, AnonymizerConfig
from .zero_knowledge import ZeroKnowledgeProver, ZeroKnowledgeVerifier
from .differential_privacy import DifferentialPrivacy, PrivacyBudget

logger = logging.getLogger(__name__)

@dataclass
class PrivacyPolicy:
    """Define a privacy policy for the Quantum Trail system."""
    
    # Unique policy identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Human-readable name
    name: str = "Default Privacy Policy"
    
    # Human-readable description
    description: str = "Default privacy policy for Quantum Trail"
    
    # Anonymization settings
    anonymizer_config: AnonymizerConfig = field(default_factory=AnonymizerConfig)
    
    # Differential privacy settings
    privacy_budget: PrivacyBudget = field(default_factory=PrivacyBudget)
    
    # Use quantum-resistant algorithms
    quantum_resistant: bool = True
    
    # Enable zero-knowledge proofs
    enable_zkp: bool = True
    
    # Enable differential privacy
    enable_dp: bool = True
    
    # Data retention period in seconds (default: 30 days)
    data_retention_period: int = 30 * 86400
    
    # Consent requirements
    require_explicit_consent: bool = True
    
    # Audit logging level
    audit_level: str = "detailed"  # minimal, basic, detailed, comprehensive
    
    # Created timestamp
    created_at: float = field(default_factory=time.time)
    
    # Updated timestamp
    updated_at: float = field(default_factory=time.time)


class PrivacyManager:
    """
    Unified manager for privacy mechanisms in the Quantum Trail.
    
    This class orchestrates the various privacy mechanisms:
    - Anonymization
    - Zero-knowledge proofs
    - Differential privacy
    
    It provides a unified interface for applying privacy protections
    according to configurable policies.
    """
    
    def __init__(self, policy: PrivacyPolicy = None):
        """
        Initialize the Privacy Manager.
        
        Args:
            policy: Privacy policy to apply
        """
        self.policy = policy or PrivacyPolicy()
        
        # Initialize components based on policy
        self.anonymizer = Anonymizer(config=self.policy.anonymizer_config)
        
        self.zkp_prover = None
        self.zkp_verifier = None
        if self.policy.enable_zkp:
            self.zkp_prover = ZeroKnowledgeProver(quantum_resistant=self.policy.quantum_resistant)
            self.zkp_verifier = ZeroKnowledgeVerifier(quantum_resistant=self.policy.quantum_resistant)
        
        self.dp_engine = None
        if self.policy.enable_dp:
            self.dp_engine = DifferentialPrivacy(default_budget=self.policy.privacy_budget)
        
        # Audit log
        self.audit_log = []
        
        logger.info(f"Privacy Manager initialized with policy: {self.policy.name}")
    
    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize data according to the privacy policy.
        
        Args:
            data: Data to anonymize
            
        Returns:
            Anonymized data
        """
        result = self.anonymizer.anonymize(data)
        
        # Log the operation if detailed auditing is enabled
        if self.policy.audit_level in ["detailed", "comprehensive"]:
            self._log_operation("anonymize", {
                "data_fields": list(data.keys()),
                "anonymized_fields": [
                    field for field in data.keys() 
                    if field in self.policy.anonymizer_config.sensitive_fields
                ]
            })
        
        return result
    
    def create_zero_knowledge_proof(self, proof_type: str, data: Any, 
                                   statement: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a zero-knowledge proof.
        
        Args:
            proof_type: Type of proof to create
            data: Private data
            statement: Statement to prove
            
        Returns:
            Proof object or None if ZKP is disabled
        """
        if not self.policy.enable_zkp or not self.zkp_prover:
            logger.warning("Zero-knowledge proofs are disabled in privacy policy")
            return None
        
        proof = self.zkp_prover.create_proof(proof_type, data, statement)
        
        # Log the operation
        self._log_operation("create_zkp", {
            "proof_type": proof_type,
            "proof_id": proof.get("id"),
            "statement_fields": list(statement.keys())
        })
        
        return proof
    
    def verify_zero_knowledge_proof(self, proof: Dict[str, Any], 
                                   verification_data: Dict[str, Any] = None) -> bool:
        """
        Verify a zero-knowledge proof.
        
        Args:
            proof: Proof to verify
            verification_data: Additional verification data
            
        Returns:
            True if proof is valid, False otherwise or if ZKP is disabled
        """
        if not self.policy.enable_zkp or not self.zkp_verifier:
            logger.warning("Zero-knowledge proofs are disabled in privacy policy")
            return False
        
        result = self.zkp_verifier.verify_proof(proof, verification_data)
        
        # Log the operation
        self._log_operation("verify_zkp", {
            "proof_type": proof.get("type"),
            "proof_id": proof.get("id"),
            "result": result
        })
        
        return result
    
    def apply_differential_privacy(self, operation: str, data: Any, 
                                  sensitivity: float) -> Any:
        """
        Apply differential privacy to data.
        
        Args:
            operation: Operation type (laplace, gaussian, histogram, mean, quantile)
            data: Data to privatize
            sensitivity: Data sensitivity
            
        Returns:
            Privatized data or None if DP is disabled
        """
        if not self.policy.enable_dp or not self.dp_engine:
            logger.warning("Differential privacy is disabled in privacy policy")
            return None
        
        result = None
        
        if operation == "laplace":
            if not isinstance(data, (int, float)):
                logger.error("Data must be numeric for Laplace mechanism")
                return None
            result = self.dp_engine.add_laplace_noise(data, sensitivity, self.policy.privacy_budget)
            
        elif operation == "gaussian":
            if not isinstance(data, (int, float)):
                logger.error("Data must be numeric for Gaussian mechanism")
                return None
            result = self.dp_engine.add_gaussian_noise(data, sensitivity, self.policy.privacy_budget)
            
        elif operation == "histogram":
            if not isinstance(data, dict):
                logger.error("Data must be a dictionary for histogram privatization")
                return None
            result = self.dp_engine.privatize_histogram(data, sensitivity, self.policy.privacy_budget)
            
        elif operation == "mean":
            if not isinstance(data, list) or not all(isinstance(x, (int, float)) for x in data):
                logger.error("Data must be a list of numbers for mean privatization")
                return None
            result = self.dp_engine.privatize_mean(data, sensitivity, self.policy.privacy_budget)
            
        elif operation == "quantile":
            if not isinstance(data, dict) or "data" not in data or "quantile" not in data:
                logger.error("Data must contain 'data' list and 'quantile' value")
                return None
            result = self.dp_engine.privatize_quantile(
                data["data"], data["quantile"], sensitivity, self.policy.privacy_budget
            )
            
        else:
            logger.error(f"Unsupported differential privacy operation: {operation}")
            return None
        
        # Log the operation
        self._log_operation("differential_privacy", {
            "operation": operation,
            "sensitivity": sensitivity,
            "data_type": str(type(data)),
            "has_result": result is not None
        })
        
        return result
    
    def check_data_retention(self, data_timestamp: float) -> bool:
        """
        Check if data should be retained based on retention policy.
        
        Args:
            data_timestamp: Timestamp when data was created
            
        Returns:
            True if data should be retained, False if it should be deleted
        """
        current_time = time.time()
        age = current_time - data_timestamp
        
        should_retain = age <= self.policy.data_retention_period
        
        # Log the check if comprehensive auditing is enabled
        if self.policy.audit_level == "comprehensive":
            self._log_operation("retention_check", {
                "data_age_seconds": age,
                "retention_limit_seconds": self.policy.data_retention_period,
                "should_retain": should_retain
            })
        
        return should_retain
    
    def update_policy(self, new_policy: PrivacyPolicy) -> None:
        """
        Update the privacy policy.
        
        Args:
            new_policy: New privacy policy
        """
        old_policy_id = self.policy.id
        self.policy = new_policy
        self.policy.updated_at = time.time()
        
        # Reinitialize components with new policy
        self.anonymizer = Anonymizer(config=self.policy.anonymizer_config)
        
        if self.policy.enable_zkp:
            self.zkp_prover = ZeroKnowledgeProver(quantum_resistant=self.policy.quantum_resistant)
            self.zkp_verifier = ZeroKnowledgeVerifier(quantum_resistant=self.policy.quantum_resistant)
        else:
            self.zkp_prover = None
            self.zkp_verifier = None
        
        if self.policy.enable_dp:
            self.dp_engine = DifferentialPrivacy(default_budget=self.policy.privacy_budget)
        else:
            self.dp_engine = None
        
        # Log the policy update
        self._log_operation("policy_update", {
            "old_policy_id": old_policy_id,
            "new_policy_id": self.policy.id,
            "new_policy_name": self.policy.name
        })
        
        logger.info(f"Privacy policy updated to: {self.policy.name}")
    
    def _log_operation(self, operation_type: str, details: Dict[str, Any]) -> None:
        """
        Log a privacy operation for auditing.
        
        Args:
            operation_type: Type of operation
            details: Operation details
        """
        # Skip logging if minimal audit level
        if self.policy.audit_level == "minimal":
            return
        
        log_entry = {
            "timestamp": time.time(),
            "operation": operation_type,
            "policy_id": self.policy.id,
            "policy_name": self.policy.name
        }
        
        # Add details based on audit level
        if self.policy.audit_level in ["detailed", "comprehensive"]:
            log_entry["details"] = details
        
        self.audit_log.append(log_entry)
        
        # Trim log if it gets too long
        max_log_entries = 10000
        if len(self.audit_log) > max_log_entries:
            self.audit_log = self.audit_log[-max_log_entries:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the privacy manager.
        
        Returns:
            Status information
        """
        dp_stats = None
        if self.dp_engine:
            dp_stats = self.dp_engine.get_query_stats()
        
        anonymizer_stats = None
        if self.anonymizer:
            anonymizer_stats = self.anonymizer.get_stats()
        
        # Check remaining privacy budget
        remaining_budget_pct = None
        if self.policy.enable_dp and self.policy.privacy_budget:
            remaining_budget_pct = self.policy.privacy_budget.remaining_percentage()
        
        return {
            "policy": {
                "id": self.policy.id,
                "name": self.policy.name,
                "created_at": self.policy.created_at,
                "updated_at": self.policy.updated_at,
                "quantum_resistant": self.policy.quantum_resistant,
                "data_retention_days": self.policy.data_retention_period / 86400
            },
            "features": {
                "anonymization": True,  # Always enabled
                "zero_knowledge_proofs": self.policy.enable_zkp,
                "differential_privacy": self.policy.enable_dp
            },
            "anonymizer": anonymizer_stats,
            "differential_privacy": dp_stats,
            "remaining_privacy_budget_pct": remaining_budget_pct,
            "audit_log_entries": len(self.audit_log),
            "audit_level": self.policy.audit_level
        }

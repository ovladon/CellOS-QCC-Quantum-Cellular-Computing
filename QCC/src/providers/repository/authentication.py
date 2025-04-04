"""
Authentication system for Quantum Cellular Computing repository.

This module provides functionality for authenticating users and services
that interact with the repository, ensuring that only authorized entities
can access, publish, or modify cells.
"""

import os
import time
import json
import logging
import hashlib
import hmac
import base64
import secrets
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from qcc.common.exceptions import AuthenticationError, AuthorizationError
from qcc.providers.repository.storage import StorageManager

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manages authentication for the cell repository.
    
    This class provides functionality for authenticating users and services,
    generating and validating access tokens, and managing API keys.
    """
    
    def __init__(self, storage_manager: StorageManager):
        """
        Initialize the authentication manager.
        
        Args:
            storage_manager: Storage manager for accessing authentication data
        """
        self.storage_manager = storage_manager
        self.token_cache = {}  # token -> {user_id, expiry, permissions}
        self.api_key_cache = {}  # key_id -> {key, permissions, owner}
        self.secret_key = self._load_or_generate_secret()
        
    async def authenticate_user(self, username: str, password: str) -> str:
        """
        Authenticate a user and return an access token.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Access token
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Get user data
            user_data = await self._get_user_data(username)
            if not user_data:
                raise AuthenticationError("Invalid username or password")
            
            # Verify password
            if not self._verify_password(password, user_data.get("password_hash", "")):
                raise AuthenticationError("Invalid username or password")
            
            # Generate token
            token = self._generate_token(
                user_id=username,
                permissions=user_data.get("permissions", []),
                expiry_hours=24
            )
            
            # Log successful authentication
            logger.info(f"User {username} authenticated successfully")
            
            return token
            
        except Exception as e:
            if not isinstance(e, AuthenticationError):
                logger.error(f"Authentication error for user {username}: {e}")
                raise AuthenticationError("Authentication failed")
            raise
    
    async def authenticate_service(self, api_key_id: str, api_key_secret: str) -> str:
        """
        Authenticate a service using API key and return an access token.
        
        Args:
            api_key_id: API key identifier
            api_key_secret: API key secret
            
        Returns:
            Access token
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Get API key data
            api_key_data = await self._get_api_key_data(api_key_id)
            if not api_key_data:
                raise AuthenticationError("Invalid API key")
            
            # Verify API key
            if not self._verify_api_key(api_key_secret, api_key_data.get("key_hash", "")):
                raise AuthenticationError("Invalid API key")
            
            # Check if key is expired
            expiry = api_key_data.get("expiry")
            if expiry and datetime.fromisoformat(expiry) < datetime.now():
                raise AuthenticationError("API key has expired")
            
            # Generate token
            token = self._generate_token(
                user_id=api_key_data.get("owner", "service"),
                permissions=api_key_data.get("permissions", []),
                expiry_hours=12,
                service=True
            )
            
            # Log successful authentication
            logger.info(f"Service authenticated with API key {api_key_id}")
            
            return token
            
        except Exception as e:
            if not isinstance(e, AuthenticationError):
                logger.error(f"Authentication error for API key {api_key_id}: {e}")
                raise AuthenticationError("Authentication failed")
            raise
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify an access token and return the associated data.
        
        Args:
            token: Access token to verify
            
        Returns:
            Token data including user_id and permissions
            
        Raises:
            AuthenticationError: If the token is invalid or expired
        """
        try:
            # Check cache first
            if token in self.token_cache:
                token_data = self.token_cache[token]
                # Check expiry
                if token_data.get("expiry", 0) < time.time():
                    del self.token_cache[token]
                    raise AuthenticationError("Token has expired")
                return token_data
            
            # Parse token
            parts = token.split(".")
            if len(parts) != 3:
                raise AuthenticationError("Invalid token format")
            
            header_raw, payload_raw, signature = parts
            
            # Verify signature
            expected_signature = self._generate_signature(f"{header_raw}.{payload_raw}")
            if not hmac.compare_digest(signature, expected_signature):
                raise AuthenticationError("Invalid token signature")
            
            # Decode payload
            try:
                payload = json.loads(base64.urlsafe_b64decode(payload_raw + "==").decode())
            except Exception:
                raise AuthenticationError("Invalid token payload")
            
            # Check expiry
            if "exp" in payload and payload["exp"] < time.time():
                raise AuthenticationError("Token has expired")
            
            # Extract data
            token_data = {
                "user_id": payload.get("sub"),
                "permissions": payload.get("permissions", []),
                "expiry": payload.get("exp"),
                "is_service": payload.get("is_service", False)
            }
            
            # Cache valid token
            self.token_cache[token] = token_data
            
            return token_data
            
        except Exception as e:
            if not isinstance(e, AuthenticationError):
                logger.error(f"Token verification error: {e}")
                raise AuthenticationError("Token verification failed")
            raise
    
    async def create_api_key(
        self, 
        owner: str, 
        permissions: List[str], 
        expiry_days: Optional[int] = 365
    ) -> Dict[str, str]:
        """
        Create a new API key.
        
        Args:
            owner: Owner of the API key
            permissions: Permissions granted to the key
            expiry_days: Number of days until key expires (None for no expiry)
            
        Returns:
            Dictionary with key_id and key_secret
            
        Raises:
            AuthorizationError: If the operation is not authorized
        """
        try:
            # Generate key ID and secret
            key_id = f"key_{secrets.token_hex(8)}"
            key_secret = secrets.token_hex(32)
            
            # Calculate expiry date
            expiry = None
            if expiry_days is not None:
                expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat()
            
            # Hash the key for storage
            key_hash = self._hash_secret(key_secret)
            
            # Store API key data
            api_key_data = {
                "key_id": key_id,
                "key_hash": key_hash,
                "owner": owner,
                "permissions": permissions,
                "created_at": datetime.now().isoformat(),
                "expiry": expiry,
                "last_used": None
            }
            
            await self._store_api_key_data(key_id, api_key_data)
            
            # Log key creation
            logger.info(f"API key {key_id} created for {owner}")
            
            # Return key details
            return {
                "key_id": key_id,
                "key_secret": key_secret
            }
            
        except Exception as e:
            logger.error(f"Error creating API key for {owner}: {e}")
            raise AuthorizationError("Failed to create API key")
    
    async def revoke_api_key(self, key_id: str, requester: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: API key identifier
            requester: ID of user or service making the request
            
        Returns:
            True if the key was revoked, False otherwise
            
        Raises:
            AuthorizationError: If the requester is not authorized to revoke the key
        """
        try:
            # Get API key data
            api_key_data = await self._get_api_key_data(key_id)
            if not api_key_data:
                return False
            
            # Check if requester is authorized
            if requester != api_key_data.get("owner") and not await self._is_admin(requester):
                raise AuthorizationError("Not authorized to revoke this API key")
            
            # Mark key as revoked
            api_key_data["revoked"] = True
            api_key_data["revoked_at"] = datetime.now().isoformat()
            api_key_data["revoked_by"] = requester
            
            # Update key data
            await self._store_api_key_data(key_id, api_key_data)
            
            # Remove from cache
            if key_id in self.api_key_cache:
                del self.api_key_cache[key_id]
            
            # Log key revocation
            logger.info(f"API key {key_id} revoked by {requester}")
            
            return True
            
        except Exception as e:
            if not isinstance(e, AuthorizationError):
                logger.error(f"Error revoking API key {key_id}: {e}")
                raise AuthorizationError("Failed to revoke API key")
            raise
    
    async def list_api_keys(self, owner: str) -> List[Dict[str, Any]]:
        """
        List API keys for a specific owner.
        
        Args:
            owner: Owner of the API keys
            
        Returns:
            List of API key data (excluding sensitive fields)
        """
        try:
            # Get API keys directory
            keys_dir = os.path.join("auth", "api_keys")
            key_files = await self.storage_manager.list_files(keys_dir)
            
            keys = []
            for key_file in key_files:
                key_id = os.path.splitext(os.path.basename(key_file))[0]
                
                # Get key data
                key_data = await self._get_api_key_data(key_id)
                
                # Check if key belongs to owner
                if key_data and key_data.get("owner") == owner:
                    # Remove sensitive fields
                    if "key_hash" in key_data:
                        del key_data["key_hash"]
                    
                    keys.append(key_data)
            
            return keys
            
        except Exception as e:
            logger.error(f"Error listing API keys for {owner}: {e}")
            return []
    
    async def check_permission(self, token: str, required_permission: str) -> bool:
        """
        Check if a token has a specific permission.
        
        Args:
            token: Access token
            required_permission: Permission to check
            
        Returns:
            True if the token has the permission, False otherwise
        """
        try:
            # Verify token
            token_data = await self.verify_token(token)
            
            # Check for admin permission (grants all permissions)
            if "admin" in token_data.get("permissions", []):
                return True
            
            # Check for specific permission
            return required_permission in token_data.get("permissions", [])
            
        except Exception:
            return False
    
    async def _get_user_data(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from storage.
        
        Args:
            username: User's username
            
        Returns:
            User data or None if not found
        """
        user_path = os.path.join("auth", "users", f"{username}.json")
        
        try:
            return await self.storage_manager.read_json(user_path)
        except Exception:
            return None
    
    async def _get_api_key_data(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get API key data from storage.
        
        Args:
            key_id: API key identifier
            
        Returns:
            API key data or None if not found
        """
        # Check cache first
        if key_id in self.api_key_cache:
            return self.api_key_cache[key_id]
        
        key_path = os.path.join("auth", "api_keys", f"{key_id}.json")
        
        try:
            key_data = await self.storage_manager.read_json(key_path)
            
            # Check if key is revoked
            if key_data and key_data.get("revoked", False):
                return None
            
            # Cache key data
            if key_data:
                self.api_key_cache[key_id] = key_data
            
            return key_data
        except Exception:
            return None
    
    async def _store_api_key_data(self, key_id: str, key_data: Dict[str, Any]) -> None:
        """
        Store API key data in storage.
        
        Args:
            key_id: API key identifier
            key_data: API key data
        """
        key_path = os.path.join("auth", "api_keys", f"{key_id}.json")
        
        # Ensure directory exists
        await self.storage_manager.create_directory(os.path.dirname(key_path))
        
        # Write key data
        await self.storage_manager.write_json(key_path, key_data)
        
        # Update cache
        self.api_key_cache[key_id] = key_data
    
    async def _is_admin(self, user_id: str) -> bool:
        """
        Check if a user has admin privileges.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if the user is an admin, False otherwise
        """
        user_data = await self._get_user_data(user_id)
        return user_data is not None and "admin" in user_data.get("permissions", [])
    
    def _generate_token(
        self, 
        user_id: str, 
        permissions: List[str], 
        expiry_hours: int = 24,
        service: bool = False
    ) -> str:
        """
        Generate a JWT-like access token.
        
        Args:
            user_id: User identifier
            permissions: User permissions
            expiry_hours: Token expiry in hours
            service: Whether this is a service token
            
        Returns:
            JWT-like access token
        """
        # Create header
        header = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        # Create payload
        expiry = int(time.time() + expiry_hours * 3600)
        payload = {
            "sub": user_id,
            "permissions": permissions,
            "exp": expiry,
            "iat": int(time.time()),
            "is_service": service
        }
        
        # Encode header and payload
        header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        
        # Generate signature
        signature = self._generate_signature(f"{header_encoded}.{payload_encoded}")
        
        # Combine parts
        token = f"{header_encoded}.{payload_encoded}.{signature}"
        
        # Store in cache
        self.token_cache[token] = {
            "user_id": user_id,
            "permissions": permissions,
            "expiry": expiry,
            "is_service": service
        }
        
        return token
    
    def _generate_signature(self, data: str) -> str:
        """
        Generate a signature for token data.
        
        Args:
            data: Data to sign
            
        Returns:
            Base64-encoded signature
        """
        h = hmac.new(self.secret_key.encode(), data.encode(), hashlib.sha256)
        return base64.urlsafe_b64encode(h.digest()).decode().rstrip("=")
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against a stored hash.
        
        Args:
            password: Password to verify
            password_hash: Stored password hash
            
        Returns:
            True if the password is valid, False otherwise
        """
        if not password or not password_hash:
            return False
        
        # Split hash into algorithm, salt, and digest
        try:
            algorithm, salt, stored_hash = password_hash.split("$")
            
            # Hash the provided password with the same salt
            hash_obj = hashlib.new(algorithm)
            hash_obj.update((salt + password).encode())
            computed_hash = hash_obj.hexdigest()
            
            # Compare hashes
            return hmac.compare_digest(stored_hash, computed_hash)
            
        except Exception:
            return False
    
    def _verify_api_key(self, key: str, key_hash: str) -> bool:
        """
        Verify an API key against a stored hash.
        
        Args:
            key: API key to verify
            key_hash: Stored key hash
            
        Returns:
            True if the key is valid, False otherwise
        """
        if not key or not key_hash:
            return False
        
        # Split hash into algorithm, salt, and digest
        try:
            algorithm, salt, stored_hash = key_hash.split("$")
            
            # Hash the provided key with the same salt
            hash_obj = hashlib.new(algorithm)
            hash_obj.update((salt + key).encode())
            computed_hash = hash_obj.hexdigest()
            
            # Compare hashes
            return hmac.compare_digest(stored_hash, computed_hash)
            
        except Exception:
            return False
    
    def _hash_secret(self, secret: str) -> str:
        """
        Hash a secret (password or API key) for storage.
        
        Args:
            secret: Secret to hash
            
        Returns:
            Hash string in format "algorithm$salt$hash"
        """
        algorithm = "sha256"
        salt = secrets.token_hex(16)
        
        hash_obj = hashlib.new(algorithm)
        hash_obj.update((salt + secret).encode())
        digest = hash_obj.hexdigest()
        
        return f"{algorithm}${salt}${digest}"
    
    def _load_or_generate_secret(self) -> str:
        """
        Load or generate a secret key for signing tokens.
        
        Returns:
            Secret key
        """
        # In a real implementation, this would load from a secure storage
        # For demo purposes, we generate a new key each time
        return secrets.token_hex(32)
    
    async def create_user(
        self, 
        username: str, 
        password: str, 
        permissions: List[str] = None,
        creator: Optional[str] = None
    ) -> bool:
        """
        Create a new user.
        
        Args:
            username: User's username
            password: User's password
            permissions: User's permissions
            creator: Creator of the user
            
        Returns:
            True if the user was created, False otherwise
        """
        try:
            # Check if user already exists
            existing_user = await self._get_user_data(username)
            if existing_user:
                return False
            
            # Hash the password
            password_hash = self._hash_secret(password)
            
            # Create user data
            user_data = {
                "username": username,
                "password_hash": password_hash,
                "permissions": permissions or ["read"],
                "created_at": datetime.now().isoformat(),
                "created_by": creator
            }
            
            # Store user data
            user_path = os.path.join("auth", "users", f"{username}.json")
            
            # Ensure directory exists
            await self.storage_manager.create_directory(os.path.dirname(user_path))
            
            # Write user data
            await self.storage_manager.write_json(user_path, user_data)
            
            # Log user creation
            logger.info(f"User {username} created")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return False

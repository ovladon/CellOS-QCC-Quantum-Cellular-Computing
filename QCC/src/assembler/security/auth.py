"""
Authentication and Authorization Module for QCC Assembler.

This module provides authentication and authorization services for the QCC Assembler,
ensuring that only authorized users and components can interact with the system.
It implements various authentication methods and enforces permission-based access control.

Authentication methods supported:
- API Key-based authentication
- Token-based authentication (JWT)
- Certificate-based authentication
- OAuth 2.0 integration

Authorization features:
- Role-based access control
- Capability-based permissions
- Dynamic permission adjustment
- Quantum trail verification
"""

import os
import time
import uuid
import logging
import hashlib
import hmac
import base64
import json
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from datetime import datetime, timedelta
from functools import wraps

import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature

# Local imports
from qcc.common.exceptions import AuthenticationError, AuthorizationError, SecurityError
from qcc.common.utils import safe_dict_get
from qcc.quantum_trail import QuantumTrailManager

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Authentication and Authorization Manager for the QCC Assembler.
    
    This class provides methods for authenticating users and components, as well as
    authorizing access to specific capabilities based on roles and permissions.
    """
    
    def __init__(self, config: Dict[str, Any], quantum_trail_manager: Optional[QuantumTrailManager] = None):
        """
        Initialize the Authentication Manager.
        
        Args:
            config: Configuration dictionary with authentication settings
            quantum_trail_manager: Optional quantum trail manager for signature verification
        """
        self.config = config
        self.quantum_trail_manager = quantum_trail_manager
        
        # Authentication settings
        self.auth_settings = safe_dict_get(config, 'assembler.security', {})
        self.auth_enabled = safe_dict_get(self.auth_settings, 'authentication_required', True)
        self.auth_service_url = safe_dict_get(self.auth_settings, 'auth_service_url', None)
        
        # Load secrets and keys
        self._load_secrets()
        
        # User session cache
        self.session_cache = {}
        
        # Permission maps
        self.role_permission_map = self._load_role_permissions()
        self.capability_permission_map = self._load_capability_permissions()
        
        logger.info("AuthManager initialized with authentication %s", 
                   "enabled" if self.auth_enabled else "disabled")

    def _load_secrets(self) -> None:
        """Load authentication secrets and keys from configuration or environment."""
        # API Keys
        self.api_keys = safe_dict_get(self.auth_settings, 'api_keys', {})
        
        # Load API keys from environment if configured
        api_key_env_prefix = safe_dict_get(self.auth_settings, 'api_key_env_prefix', 'QCC_API_KEY_')
        for env_var, value in os.environ.items():
            if env_var.startswith(api_key_env_prefix):
                key_id = env_var[len(api_key_env_prefix):].lower()
                self.api_keys[key_id] = value
                logger.debug(f"Loaded API key {key_id} from environment")
        
        # JWT settings
        jwt_settings = safe_dict_get(self.auth_settings, 'jwt', {})
        self.jwt_secret = jwt_settings.get('secret')
        
        # Load JWT secret from environment if not in config
        if not self.jwt_secret:
            jwt_secret_env = jwt_settings.get('secret_env', 'QCC_JWT_SECRET')
            self.jwt_secret = os.environ.get(jwt_secret_env)
        
        if not self.jwt_secret and self.auth_enabled:
            logger.warning("JWT secret not configured. JWT authentication will not work.")
        
        self.jwt_algorithm = jwt_settings.get('algorithm', 'HS256')
        self.jwt_expiration = jwt_settings.get('expiration_seconds', 3600)  # 1 hour default
        self.jwt_issuer = jwt_settings.get('issuer', 'qcc-assembler')
        self.jwt_audience = jwt_settings.get('audience', 'qcc-system')
        
        # Certificate settings
        cert_settings = safe_dict_get(self.auth_settings, 'certificates', {})
        self.cert_path = cert_settings.get('ca_cert_path')
        
        # Load CA cert from environment if not in config
        if not self.cert_path:
            cert_path_env = cert_settings.get('ca_cert_path_env', 'QCC_CA_CERT_PATH')
            self.cert_path = os.environ.get(cert_path_env)
        
        # Load CA cert if path is provided
        self.ca_cert = None
        if self.cert_path and os.path.exists(self.cert_path):
            try:
                with open(self.cert_path, 'rb') as cert_file:
                    self.ca_cert = x509.load_pem_x509_certificate(
                        cert_file.read(), default_backend())
                logger.info(f"Loaded CA certificate from {self.cert_path}")
            except Exception as e:
                logger.error(f"Failed to load CA certificate: {e}")
        elif self.auth_enabled and cert_settings.get('required', False):
            logger.warning("CA certificate not configured. Certificate authentication will not work.")
        
        # OAuth settings
        self.oauth_settings = safe_dict_get(self.auth_settings, 'oauth', {})
        self.oauth_client_id = self.oauth_settings.get('client_id')
        self.oauth_client_secret = self.oauth_settings.get('client_secret')
        
        # Load OAuth credentials from environment if not in config
        if not self.oauth_client_id:
            client_id_env = self.oauth_settings.get('client_id_env', 'QCC_OAUTH_CLIENT_ID')
            self.oauth_client_id = os.environ.get(client_id_env)
        
        if not self.oauth_client_secret:
            client_secret_env = self.oauth_settings.get('client_secret_env', 'QCC_OAUTH_CLIENT_SECRET')
            self.oauth_client_secret = os.environ.get(client_secret_env)
        
        if self.auth_enabled and self.oauth_settings.get('enabled', False) and (
                not self.oauth_client_id or not self.oauth_client_secret):
            logger.warning("OAuth credentials not configured. OAuth authentication will not work.")

    def _load_role_permissions(self) -> Dict[str, Set[str]]:
        """
        Load role-to-permission mappings from configuration.
        
        Returns:
            Dictionary mapping role names to sets of permission strings
        """
        role_permissions = {}
        roles_config = safe_dict_get(self.auth_settings, 'roles', {})
        
        for role_name, role_config in roles_config.items():
            permissions = set(role_config.get('permissions', []))
            role_permissions[role_name] = permissions
            logger.debug(f"Loaded role {role_name} with {len(permissions)} permissions")
        
        # Always include default roles if not explicitly configured
        if 'admin' not in role_permissions:
            role_permissions['admin'] = {'*'}  # Admin role has all permissions
            logger.debug("Added default admin role with all permissions")
        
        if 'user' not in role_permissions:
            # Basic user permissions
            role_permissions['user'] = {
                'assemble:solution', 'release:solution', 'execute:capability',
                'read:solution', 'suspend:solution', 'resume:solution'
            }
            logger.debug("Added default user role with basic permissions")
        
        if 'guest' not in role_permissions:
            # Very limited guest permissions
            role_permissions['guest'] = {
                'assemble:solution', 'release:solution', 'execute:capability'
            }
            logger.debug("Added default guest role with limited permissions")
        
        return role_permissions

    def _load_capability_permissions(self) -> Dict[str, str]:
        """
        Load capability-to-permission mappings from configuration.
        
        Returns:
            Dictionary mapping capability names to required permission strings
        """
        capability_permissions = {}
        capabilities_config = safe_dict_get(self.auth_settings, 'capabilities', {})
        
        for capability, permission in capabilities_config.items():
            capability_permissions[capability] = permission
            logger.debug(f"Capability {capability} requires permission {permission}")
        
        # Default capability permissions if not explicitly configured
        default_capabilities = {
            'file_system': 'system:file_access',
            'network_interface': 'system:network_access',
            'ui_rendering': 'user:ui_access',
            'text_generation': 'user:content_generation',
            'data_visualization': 'user:data_visualization',
            'media_player': 'user:media_access'
        }
        
        for capability, permission in default_capabilities.items():
            if capability not in capability_permissions:
                capability_permissions[capability] = permission
                logger.debug(f"Added default permission {permission} for capability {capability}")
        
        return capability_permissions

    def authenticate(self, request: Any) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate a request using available authentication methods.
        
        Args:
            request: The request object containing authentication information
            
        Returns:
            Tuple containing:
            - Authentication success (True/False)
            - User/client context (empty dict if authentication fails)
            
        Raises:
            AuthenticationError: If authentication fails and failure_raises_exception is True
        """
        if not self.auth_enabled:
            # Authentication is disabled, return default user context
            return True, {
                'user_id': 'anonymous',
                'roles': ['user'],
                'authenticated': False,
                'auth_method': 'none'
            }
        
        # Extract authentication information from request
        auth_header = getattr(request, 'headers', {}).get('Authorization', '')
        api_key = getattr(request, 'headers', {}).get('X-API-Key', '')
        client_cert = getattr(request, 'client_cert', None)
        
        # Try authentication methods in order
        # 1. API Key authentication
        if api_key:
            success, context = self._authenticate_api_key(api_key)
            if success:
                return True, context
        
        # 2. Bearer token (JWT) authentication
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            success, context = self._authenticate_jwt(token)
            if success:
                return True, context
        
        # 3. Certificate-based authentication
        if client_cert:
            success, context = self._authenticate_certificate(client_cert)
            if success:
                return True, context
        
        # 4. Basic auth (for OAuth token request only)
        if auth_header.startswith('Basic '):
            credentials = auth_header[6:]  # Remove 'Basic ' prefix
            success, context = self._authenticate_basic(credentials)
            if success:
                return True, context
        
        # No authentication method succeeded
        logger.warning("Authentication failed for request")
        return False, {}

    def _authenticate_api_key(self, api_key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate using API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple containing:
            - Authentication success (True/False)
            - User/client context (empty dict if authentication fails)
        """
        # Check if API key exists in key store
        for key_id, stored_key in self.api_keys.items():
            if hmac.compare_digest(api_key, stored_key):
                logger.info(f"Authenticated request with API key {key_id}")
                
                # Get associated permissions for this API key
                api_key_config = safe_dict_get(self.auth_settings, f'api_key_configs.{key_id}', {})
                roles = api_key_config.get('roles', ['user'])
                permissions = api_key_config.get('permissions', [])
                
                return True, {
                    'user_id': f'api:{key_id}',
                    'roles': roles,
                    'permissions': permissions,
                    'authenticated': True,
                    'auth_method': 'api_key',
                    'key_id': key_id
                }
        
        logger.warning("API key authentication failed - invalid key")
        return False, {}

    def _authenticate_jwt(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate using JWT token.
        
        Args:
            token: The JWT token to validate
            
        Returns:
            Tuple containing:
            - Authentication success (True/False)
            - User/client context (empty dict if authentication fails)
        """
        if not self.jwt_secret:
            logger.error("JWT authentication failed - JWT secret not configured")
            return False, {}
        
        try:
            # Decode and verify JWT token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={
                    'verify_signature': True,
                    'verify_exp': True,
                    'verify_nbf': True,
                    'verify_iat': True,
                    'verify_aud': bool(self.jwt_audience),
                    'verify_iss': bool(self.jwt_issuer),
                    'require_exp': True
                },
                audience=self.jwt_audience,
                issuer=self.jwt_issuer
            )
            
            # Extract user info from payload
            user_id = payload.get('sub')
            roles = payload.get('roles', ['user'])
            permissions = payload.get('permissions', [])
            name = payload.get('name', 'Unknown User')
            
            # Check if token is in session cache for quicker subsequent authentication
            token_id = payload.get('jti')
            if token_id:
                self.session_cache[token_id] = {
                    'user_id': user_id,
                    'roles': roles,
                    'permissions': permissions,
                    'name': name,
                    'exp': payload.get('exp')
                }
            
            logger.info(f"Authenticated user {user_id} using JWT token")
            
            return True, {
                'user_id': user_id,
                'roles': roles,
                'permissions': permissions,
                'name': name,
                'authenticated': True,
                'auth_method': 'jwt',
                'token_id': token_id
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT authentication failed - token expired")
            return False, {}
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT authentication failed - invalid token: {e}")
            return False, {}
        except Exception as e:
            logger.error(f"JWT authentication failed - unexpected error: {e}")
            return False, {}

    def _authenticate_certificate(self, client_cert: Any) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate using client certificate.
        
        Args:
            client_cert: The client certificate to validate
            
        Returns:
            Tuple containing:
            - Authentication success (True/False)
            - User/client context (empty dict if authentication fails)
        """
        if not self.ca_cert:
            logger.error("Certificate authentication failed - CA certificate not configured")
            return False, {}
        
        try:
            # Parse client certificate
            cert = x509.load_pem_x509_certificate(
                client_cert.encode('utf-8') if isinstance(client_cert, str) else client_cert,
                default_backend()
            )
            
            # Verify certificate was issued by our CA
            # In a production environment, you would use a proper certificate validation chain
            # This is a simplified example
            issuer = cert.issuer
            ca_subject = self.ca_cert.subject
            
            if issuer != ca_subject:
                logger.warning("Certificate authentication failed - untrusted issuer")
                return False, {}
            
            # Check certificate expiration
            if datetime.utcnow() > cert.not_valid_after:
                logger.warning("Certificate authentication failed - certificate expired")
                return False, {}
            
            if datetime.utcnow() < cert.not_valid_before:
                logger.warning("Certificate authentication failed - certificate not yet valid")
                return False, {}
            
            # Extract user info from certificate
            subject = cert.subject
            user_id = None
            name = None
            roles = ['user']  # Default role
            
            for attr in subject:
                if attr.oid.dotted_string == '2.5.4.3':  # Common Name
                    name = attr.value
                elif attr.oid.dotted_string == '2.5.4.45':  # uniqueIdentifier
                    user_id = attr.value
            
            # Extract roles from certificate extensions if available
            for extension in cert.extensions:
                if extension.oid.dotted_string == '2.5.29.17':  # Subject Alternative Name
                    # Custom logic to extract roles from SAN extension
                    # This is just an example and should be adapted to your certificate structure
                    pass
            
            if not user_id:
                user_id = f"cert:{hashlib.sha256(cert.public_bytes(encoding=x509.Encoding.PEM)).hexdigest()[:8]}"
            
            logger.info(f"Authenticated user {user_id} using client certificate")
            
            return True, {
                'user_id': user_id,
                'name': name,
                'roles': roles,
                'authenticated': True,
                'auth_method': 'certificate',
                'certificate_fingerprint': hashlib.sha256(cert.public_bytes(encoding=x509.Encoding.PEM)).hexdigest()
            }
            
        except Exception as e:
            logger.error(f"Certificate authentication failed - error: {e}")
            return False, {}

    def _authenticate_basic(self, credentials: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate using Basic Auth (mainly for OAuth token requests).
        
        Args:
            credentials: Base64 encoded username:password string
            
        Returns:
            Tuple containing:
            - Authentication success (True/False)
            - User/client context (empty dict if authentication fails)
        """
        try:
            # Decode credentials
            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            # For OAuth client credentials
            if self.oauth_settings.get('enabled', False) and username == self.oauth_client_id:
                if hmac.compare_digest(password, self.oauth_client_secret):
                    logger.info(f"Authenticated OAuth client {username}")
                    return True, {
                        'client_id': username,
                        'authenticated': True,
                        'auth_method': 'basic',
                        'oauth_client': True
                    }
            
            # Basic auth for user authentication (not recommended for production)
            user_auth_enabled = safe_dict_get(self.auth_settings, 'basic_auth.enabled', False)
            if user_auth_enabled:
                user_db = safe_dict_get(self.auth_settings, 'basic_auth.users', {})
                if username in user_db:
                    stored_password_hash = user_db[username].get('password_hash')
                    salt = user_db[username].get('salt', '')
                    
                    # Hash the provided password with the stored salt
                    password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
                    
                    if hmac.compare_digest(password_hash, stored_password_hash):
                        roles = user_db[username].get('roles', ['user'])
                        logger.info(f"Authenticated user {username} using basic auth")
                        return True, {
                            'user_id': username,
                            'roles': roles,
                            'authenticated': True,
                            'auth_method': 'basic'
                        }
            
            logger.warning(f"Basic auth failed for {username}")
            return False, {}
            
        except Exception as e:
            logger.error(f"Basic authentication failed - error: {e}")
            return False, {}

    def authorize(self, context: Dict[str, Any], permission: str) -> bool:
        """
        Check if the authenticated user/client has permission for an action.
        
        Args:
            context: User/client context from authentication
            permission: Permission string to check
            
        Returns:
            True if authorized, False otherwise
        """
        if not self.auth_enabled:
            # Authorization is disabled
            return True
        
        # Check if user is authenticated
        if not context.get('authenticated', False):
            logger.warning("Authorization failed - user not authenticated")
            return False
        
        # Check explicit permissions in user context
        explicit_permissions = context.get('permissions', [])
        if permission in explicit_permissions or '*' in explicit_permissions:
            return True
        
        # Check permissions based on roles
        roles = context.get('roles', [])
        for role in roles:
            if role in self.role_permission_map:
                role_permissions = self.role_permission_map[role]
                if permission in role_permissions or '*' in role_permissions:
                    return True
        
        # Special case for admin role
        if 'admin' in roles:
            return True
        
        logger.warning(f"Authorization failed - permission {permission} denied for user {context.get('user_id')}")
        return False

    def authorize_capability(self, context: Dict[str, Any], capability: str) -> bool:
        """
        Check if the authenticated user/client has permission to use a capability.
        
        Args:
            context: User/client context from authentication
            capability: Capability name to check
            
        Returns:
            True if authorized, False otherwise
        """
        if not self.auth_enabled:
            # Authorization is disabled
            return True
        
        # Check if capability requires a permission
        if capability in self.capability_permission_map:
            required_permission = self.capability_permission_map[capability]
            return self.authorize(context, required_permission)
        
        # If capability has no specific permission requirement, default to authorized
        return True

    def generate_token(self, user_id: str, roles: List[str], 
                      permissions: Optional[List[str]] = None, 
                      name: Optional[str] = None,
                      expiration_seconds: Optional[int] = None) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user_id: Unique identifier for the user
            roles: List of role names
            permissions: Optional list of explicit permissions
            name: Optional user display name
            expiration_seconds: Optional token expiration in seconds
            
        Returns:
            JWT token string
            
        Raises:
            SecurityError: If JWT secret is not configured
        """
        if not self.jwt_secret:
            raise SecurityError("JWT secret not configured")
        
        # Default expiration time
        if expiration_seconds is None:
            expiration_seconds = self.jwt_expiration
        
        # Create token payload
        payload = {
            'sub': user_id,
            'roles': roles,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=expiration_seconds),
            'jti': str(uuid.uuid4())
        }
        
        # Add optional claims
        if self.jwt_issuer:
            payload['iss'] = self.jwt_issuer
        
        if self.jwt_audience:
            payload['aud'] = self.jwt_audience
        
        if permissions:
            payload['permissions'] = permissions
            
        if name:
            payload['name'] = name
        
        # Sign and encode token
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store in session cache for faster validation
        self.session_cache[payload['jti']] = {
            'user_id': user_id,
            'roles': roles,
            'permissions': permissions,
            'name': name,
            'exp': payload['exp']
        }
        
        return token

    def revoke_token(self, token_id: str) -> bool:
        """
        Revoke a JWT token by removing it from the session cache.
        
        Args:
            token_id: The token's unique identifier (jti claim)
            
        Returns:
            True if token was found and revoked, False otherwise
        """
        if token_id in self.session_cache:
            del self.session_cache[token_id]
            logger.info(f"Revoked token {token_id}")
            return True
        
        logger.warning(f"Token {token_id} not found in session cache")
        return False

    def cleanup_sessions(self) -> int:
        """
        Clean up expired sessions from the session cache.
        
        Returns:
            Number of expired sessions removed
        """
        now = datetime.utcnow()
        expired_tokens = []
        
        for token_id, session in self.session_cache.items():
            expiration = session.get('exp')
            if expiration and datetime.fromtimestamp(expiration) < now:
                expired_tokens.append(token_id)
        
        # Remove expired sessions
        for token_id in expired_tokens:
            del self.session_cache[token_id]
            
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
            
        return len(expired_tokens)

    def verify_quantum_signature(self, quantum_signature: str, context: Dict[str, Any]) -> bool:
        """
        Verify a quantum signature against the quantum trail system.
        
        Args:
            quantum_signature: The quantum signature to verify
            context: User/client context from authentication
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.quantum_trail_manager:
            logger.warning("Quantum signature verification failed - quantum trail manager not available")
            return False
        
        try:
            # Verify signature with quantum trail manager
            verification_result = self.quantum_trail_manager.verify_signature(
                quantum_signature, user_id=context.get('user_id'))
            
            if not verification_result:
                logger.warning(f"Quantum signature verification failed for user {context.get('user_id')}")
                
            return verification_result
            
        except Exception as e:
            logger.error(f"Quantum signature verification error: {e}")
            return False

# Authentication decorator for route handlers
def requires_auth(permission: Optional[str] = None, capability: Optional[str] = None):
    """
    Decorator to enforce authentication and authorization on route handlers.
    
    Args:
        permission: Optional permission string required for this route
        capability: Optional capability name required for this route
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get auth manager from assembler instance
            auth_manager = getattr(self, 'auth_manager', None)
            if not auth_manager:
                raise SecurityError("Authentication manager not available")
            
            # Get request object (first positional argument after self)
            request = args[0] if args else None
            if not request:
                raise SecurityError("Request object not provided")
            
            # Authenticate the request
            auth_success, context = auth_manager.authenticate(request)
            if not auth_success:
                raise AuthenticationError("Authentication required")
            
            # Authorize if permission specified
            if permission and not auth_manager.authorize(context, permission):
                raise AuthorizationError(f"Permission denied: {permission}")
                
            # Authorize if capability specified
            if capability and not auth_manager.authorize_capability(context, capability):
                raise AuthorizationError(f"Permission denied for capability: {capability}")
            
            # Add user context to request for use in handler
            setattr(request, 'user_context', context)
            
            # Call the original handler
            return await func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator

"""
Network Interface Cell Implementation for QCC

This cell provides network connectivity capabilities for the QCC system,
enabling HTTP/HTTPS requests, WebSocket connections, and basic network
diagnostics.
"""

import asyncio
import logging
import time
import json
import socket
import ssl
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple, Union

from qcc.cells import BaseCell
from qcc.common.exceptions import CellError, NetworkError, SecurityError

logger = logging.getLogger(__name__)

class NetworkInterfaceCell(BaseCell):
    """
    A system cell that provides network connectivity functionality.
    
    This cell enables:
    - HTTP/HTTPS requests (GET, POST, PUT, DELETE, etc.)
    - WebSocket connections
    - Connection pooling
    - Basic network diagnostics (ping, DNS lookups, etc.)
    - Local network discovery
    
    As a system-level cell, it applies strict security policies to
    prevent unauthorized network access.
    """
    
    def initialize(self, parameters):
        """
        Initialize the network interface cell with parameters.
        
        Args:
            parameters: Initialization parameters including cell_id and context
        
        Returns:
            Initialization result with capabilities and requirements
        """
        super().initialize(parameters)
        
        # Register capabilities
        self.register_capability("http_request", self.http_request)
        self.register_capability("websocket_connect", self.websocket_connect)
        self.register_capability("network_diagnostics", self.network_diagnostics)
        self.register_capability("discover_services", self.discover_services)
        
        # Initialize connection pools and caches
        self.connection_pools = {}
        self.dns_cache = {}
        self.active_websockets = {}
        
        # Extract security settings from parameters
        self.security_settings = parameters.get("configuration", {}).get("security_settings", {})
        
        # Default security settings
        self.security_settings.setdefault("allowed_domains", ["*"])  # "*" means all domains allowed
        self.security_settings.setdefault("allowed_ips", ["*"])      # "*" means all IPs allowed
        self.security_settings.setdefault("blocked_domains", [])
        self.security_settings.setdefault("blocked_ips", [])
        self.security_settings.setdefault("max_request_size_mb", 10)
        self.security_settings.setdefault("require_https", True)
        self.security_settings.setdefault("verify_ssl", True)
        self.security_settings.setdefault("request_timeout_sec", 30)
        
        # Extract network settings
        self.network_settings = parameters.get("configuration", {}).get("network_settings", {})
        
        # Default network settings
        self.network_settings.setdefault("max_connections", 20)
        self.network_settings.setdefault("connection_timeout_sec", 10)
        self.network_settings.setdefault("dns_cache_ttl_sec", 300)  # 5 minutes
        self.network_settings.setdefault("retry_attempts", 3)
        self.network_settings.setdefault("retry_delay_ms", 1000)
        self.network_settings.setdefault("enable_compression", True)
        
        # Initialize SSL context
        self.ssl_context = ssl.create_default_context()
        if not self.security_settings.get("verify_ssl", True):
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL certificate verification is disabled")
        
        logger.info(f"Network interface cell initialized with ID: {self.cell_id}")
        
        return self.get_initialization_result()
    
    def get_initialization_result(self):
        """Get the initialization result with capabilities and requirements."""
        return {
            "status": "success",
            "cell_id": self.cell_id,
            "capabilities": [
                {
                    "name": "http_request",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "method",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "url",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "headers",
                            "type": "object",
                            "required": False
                        },
                        {
                            "name": "body",
                            "type": "any",
                            "required": False
                        },
                        {
                            "name": "timeout",
                            "type": "number",
                            "required": False
                        },
                        {
                            "name": "verify_ssl",
                            "type": "boolean",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "status_code",
                            "type": "number"
                        },
                        {
                            "name": "headers",
                            "type": "object"
                        },
                        {
                            "name": "body",
                            "type": "any"
                        },
                        {
                            "name": "timing",
                            "type": "object"
                        }
                    ]
                },
                {
                    "name": "websocket_connect",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "url",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "headers",
                            "type": "object",
                            "required": False
                        },
                        {
                            "name": "protocols",
                            "type": "array",
                            "required": False
                        },
                        {
                            "name": "timeout",
                            "type": "number",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "connection_id",
                            "type": "string"
                        },
                        {
                            "name": "status",
                            "type": "string"
                        }
                    ]
                },
                {
                    "name": "network_diagnostics",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "operation",
                            "type": "string",
                            "required": True
                        },
                        {
                            "name": "target",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "options",
                            "type": "object",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "success",
                            "type": "boolean"
                        },
                        {
                            "name": "result",
                            "type": "any"
                        }
                    ]
                },
                {
                    "name": "discover_services",
                    "version": "1.0.0",
                    "parameters": [
                        {
                            "name": "protocol",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "network",
                            "type": "string",
                            "required": False
                        },
                        {
                            "name": "timeout",
                            "type": "number",
                            "required": False
                        }
                    ],
                    "outputs": [
                        {
                            "name": "services",
                            "type": "array"
                        }
                    ]
                }
            ],
            "resource_usage": {
                "memory_mb": 20,
                "storage_mb": 5
            }
        }
    
    async def http_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an HTTP/HTTPS request.
        
        Args:
            parameters: Request parameters
                - method: HTTP method (GET, POST, PUT, DELETE, etc.)
                - url: Target URL
                - headers: Optional request headers
                - body: Optional request body
                - timeout: Optional request timeout in seconds
                - verify_ssl: Optional SSL verification flag
        
        Returns:
            Response with status code, headers, body, and timing information
        """
        # Validate required parameters
        if "method" not in parameters:
            return self._error_response("Method parameter is required")
        
        if "url" not in parameters:
            return self._error_response("URL parameter is required")
        
        method = parameters["method"].upper()
        url = parameters["url"]
        headers = parameters.get("headers", {})
        body = parameters.get("body")
        timeout = parameters.get("timeout", self.security_settings.get("request_timeout_sec", 30))
        verify_ssl = parameters.get("verify_ssl", self.security_settings.get("verify_ssl", True))
        
        # Security checks
        try:
            self._validate_request_security(method, url, headers, body)
        except SecurityError as e:
            return self._error_response(f"Security validation failed: {str(e)}")
        
        # Parse URL
        try:
            parsed_url = urllib.parse.urlparse(url)
            if not parsed_url.netloc:
                return self._error_response("Invalid URL: missing domain")
        except Exception as e:
            return self._error_response(f"Invalid URL: {str(e)}")
        
        # Ensure HTTPS if required
        if self.security_settings.get("require_https", True) and parsed_url.scheme != "https":
            return self._error_response("HTTPS is required for network requests")
        
        # Create an SSL context for this request
        ssl_context = ssl.create_default_context()
        if not verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Prepare the request
        if isinstance(body, dict) or isinstance(body, list):
            # Convert dict/list to JSON string and set content-type
            body = json.dumps(body)
            if "content-type" not in {k.lower(): v for k, v in headers.items()}:
                headers["Content-Type"] = "application/json"
        
        # Track timing
        start_time = time.time()
        dns_start = start_time
        
        try:
            # DNS resolution
            host = parsed_url.netloc
            if ":" in host:
                host = host.split(":")[0]
            
            # Use cached DNS if available and not expired
            if host in self.dns_cache:
                cache_entry = self.dns_cache[host]
                if time.time() - cache_entry["timestamp"] < self.network_settings.get("dns_cache_ttl_sec", 300):
                    ip = cache_entry["ip"]
                    logger.debug(f"Using cached DNS for {host}: {ip}")
                else:
                    # Cache expired, resolve again
                    ip = socket.gethostbyname(host)
                    self.dns_cache[host] = {"ip": ip, "timestamp": time.time()}
                    logger.debug(f"Updated DNS cache for {host}: {ip}")
            else:
                # Not in cache, resolve
                ip = socket.gethostbyname(host)
                self.dns_cache[host] = {"ip": ip, "timestamp": time.time()}
                logger.debug(f"Added to DNS cache: {host} -> {ip}")
            
            dns_end = time.time()
            
            # Create reader/writer pair
            try:
                port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                connect_start = time.time()
                
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        host=host, 
                        port=port,
                        ssl=ssl_context if parsed_url.scheme == "https" else None
                    ),
                    timeout=self.network_settings.get("connection_timeout_sec", 10)
                )
                
                connect_end = time.time()
                
                # Construct the request
                path = parsed_url.path
                if not path:
                    path = "/"
                if parsed_url.query:
                    path += f"?{parsed_url.query}"
                
                request_lines = [f"{method} {path} HTTP/1.1", f"Host: {parsed_url.netloc}"]
                
                # Add headers
                for key, value in headers.items():
                    request_lines.append(f"{key}: {value}")
                
                # Add content length if body is present
                if body:
                    if isinstance(body, str):
                        body = body.encode('utf-8')
                    elif not isinstance(body, bytes):
                        body = str(body).encode('utf-8')
                    
                    request_lines.append(f"Content-Length: {len(body)}")
                
                # Finalize request
                request_lines.append("\r\n")
                request = "\r\n".join(request_lines).encode('utf-8')
                
                if body and isinstance(body, bytes):
                    request += body
                
                # Send request
                send_start = time.time()
                writer.write(request)
                await writer.drain()
                send_end = time.time()
                
                # Read response
                receive_start = time.time()
                
                # Read status line
                status_line = await reader.readline()
                status_parts = status_line.decode('utf-8').split()
                if len(status_parts) < 3:
                    return self._error_response("Invalid HTTP response")
                
                status_code = int(status_parts[1])
                
                # Read headers
                response_headers = {}
                while True:
                    header_line = await reader.readline()
                    if header_line == b'\r\n':
                        break
                    
                    if b':' not in header_line:
                        continue
                    
                    header_name, header_value = header_line.decode('utf-8').split(':', 1)
                    response_headers[header_name.strip()] = header_value.strip()
                
                # Read body based on Transfer-Encoding or Content-Length
                response_body = b''
                
                if "Transfer-Encoding" in response_headers and "chunked" in response_headers["Transfer-Encoding"]:
                    # Read chunked encoding
                    while True:
                        chunk_size_line = await reader.readline()
                        chunk_size = int(chunk_size_line.decode('utf-8').strip(), 16)
                        
                        if chunk_size == 0:
                            # End of chunks, read final CRLF
                            await reader.readline()
                            break
                        
                        chunk = await reader.read(chunk_size)
                        response_body += chunk
                        
                        # Read CRLF after chunk
                        await reader.readline()
                
                elif "Content-Length" in response_headers:
                    # Read by content length
                    content_length = int(response_headers["Content-Length"])
                    response_body = await reader.read(content_length)
                
                else:
                    # Read until connection closed
                    while True:
                        chunk = await reader.read(4096)
                        if not chunk:
                            break
                        response_body += chunk
                
                receive_end = time.time()
                
                # Close the connection
                writer.close()
                await writer.wait_closed()
                
                # Process response based on content type
                content_type = response_headers.get("Content-Type", "")
                response_data = None
                
                if content_type.startswith("application/json"):
                    try:
                        response_data = json.loads(response_body.decode('utf-8'))
                    except json.JSONDecodeError:
                        response_data = response_body.decode('utf-8')
                
                elif content_type.startswith("text/"):
                    response_data = response_body.decode('utf-8')
                
                else:
                    # Return binary data as base64
                    import base64
                    response_data = {
                        "type": "binary",
                        "content_type": content_type,
                        "data": base64.b64encode(response_body).decode('utf-8')
                    }
                
                # Calculate timing information
                end_time = time.time()
                timing = {
                    "total_ms": int((end_time - start_time) * 1000),
                    "dns_ms": int((dns_end - dns_start) * 1000),
                    "connect_ms": int((connect_end - connect_start) * 1000),
                    "send_ms": int((send_end - send_start) * 1000),
                    "receive_ms": int((receive_end - receive_start) * 1000)
                }
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "status_code",
                            "value": status_code,
                            "type": "number"
                        },
                        {
                            "name": "headers",
                            "value": response_headers,
                            "type": "object"
                        },
                        {
                            "name": "body",
                            "value": response_data,
                            "type": "any"
                        },
                        {
                            "name": "timing",
                            "value": timing,
                            "type": "object"
                        }
                    ],
                    "performance_metrics": {
                        "execution_time_ms": timing["total_ms"],
                        "memory_used_mb": 1.0
                    }
                }
                
            except asyncio.TimeoutError:
                return self._error_response(f"Connection timeout after {self.network_settings.get('connection_timeout_sec', 10)} seconds")
            
        except socket.gaierror as e:
            return self._error_response(f"DNS resolution failed: {str(e)}")
        
        except Exception as e:
            return self._error_response(f"HTTP request failed: {str(e)}")
    
    async def websocket_connect(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Establish a WebSocket connection.
        
        Args:
            parameters: Connection parameters
                - url: WebSocket URL (ws:// or wss://)
                - headers: Optional connection headers
                - protocols: Optional WebSocket protocols
                - timeout: Optional connection timeout
        
        Returns:
            Connection ID for subsequent WebSocket operations
        """
        if "url" not in parameters:
            return self._error_response("URL parameter is required")
        
        url = parameters["url"]
        headers = parameters.get("headers", {})
        protocols = parameters.get("protocols", [])
        timeout = parameters.get("timeout", self.network_settings.get("connection_timeout_sec", 10))
        
        # Security checks
        try:
            self._validate_request_security("WEBSOCKET", url, headers)
        except SecurityError as e:
            return self._error_response(f"Security validation failed: {str(e)}")
        
        # Parse URL
        try:
            parsed_url = urllib.parse.urlparse(url)
            if not parsed_url.netloc:
                return self._error_response("Invalid URL: missing domain")
            
            if parsed_url.scheme not in ["ws", "wss"]:
                return self._error_response("URL scheme must be ws:// or wss://")
            
        except Exception as e:
            return self._error_response(f"Invalid URL: {str(e)}")
        
        # Ensure WSS if required
        if self.security_settings.get("require_https", True) and parsed_url.scheme != "wss":
            return self._error_response("WSS is required for WebSocket connections")
        
        # In a real implementation, we would establish an actual WebSocket connection
        # For this example, we'll simulate the connection with a placeholder
        
        # Generate a connection ID
        connection_id = f"ws_{int(time.time())}_{len(self.active_websockets)}"
        
        # Store connection info
        self.active_websockets[connection_id] = {
            "url": url,
            "connected_at": time.time(),
            "status": "connected",
            "messages_sent": 0,
            "messages_received": 0,
            "last_activity": time.time()
        }
        
        logger.info(f"WebSocket connection established: {connection_id} to {url}")
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "connection_id",
                    "value": connection_id,
                    "type": "string"
                },
                {
                    "name": "status",
                    "value": "connected",
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 100,
                "memory_used_mb": 0.5
            }
        }
    
    async def network_diagnostics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform network diagnostic operations.
        
        Args:
            parameters: Diagnostic parameters
                - operation: Operation to perform (ping, dns, traceroute, check_port, whois)
                - target: Target host or IP
                - options: Operation-specific options
        
        Returns:
            Diagnostic results
        """
        if "operation" not in parameters:
            return self._error_response("Operation parameter is required")
        
        operation = parameters["operation"].lower()
        target = parameters.get("target")
        options = parameters.get("options", {})
        
        # Most operations require a target
        if operation != "local_info" and not target:
            return self._error_response("Target parameter is required")
        
        # Security checks for target
        if target:
            try:
                self._validate_target_security(target)
            except SecurityError as e:
                return self._error_response(f"Security validation failed: {str(e)}")
        
        try:
            if operation == "ping":
                # Simulate ping operation
                count = options.get("count", 4)
                timeout = options.get("timeout", 1)
                
                # Validate count
                if count > 20:
                    return self._error_response("Ping count cannot exceed 20")
                
                # Simulate ping results
                ping_results = []
                total_time = 0
                success_count = 0
                
                for i in range(count):
                    # Simulate network latency and packet loss
                    latency = 20 + (hash(f"{target}_{i}") % 80)  # 20-100ms
                    packet_loss = (hash(f"{target}_{i}_loss") % 100) < 5  # 5% packet loss
                    
                    if packet_loss:
                        ping_results.append({
                            "seq": i,
                            "success": False,
                            "error": "Request timeout"
                        })
                    else:
                        ping_results.append({
                            "seq": i,
                            "success": True,
                            "time_ms": latency
                        })
                        total_time += latency
                        success_count += 1
                
                # Calculate statistics
                packet_loss_pct = (count - success_count) / count * 100
                avg_time = total_time / success_count if success_count > 0 else 0
                
                result = {
                    "target": target,
                    "transmitted": count,
                    "received": success_count,
                    "packet_loss_pct": packet_loss_pct,
                    "avg_time_ms": avg_time,
                    "details": ping_results
                }
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "result",
                            "value": result,
                            "type": "object"
                        }
                    ]
                }
                
            elif operation == "dns":
                # Perform actual DNS lookup
                record_type = options.get("record_type", "A")
                
                # If we're simulating this, we'd return mock data
                # For a real implementation, we would use a DNS library
                
                # For this example, we'll perform a real A record lookup
                try:
                    ip = socket.gethostbyname(target)
                    
                    result = {
                        "target": target,
                        "record_type": record_type,
                        "records": [ip],
                        "ttl": 300  # Simulated TTL
                    }
                    
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "success",
                                "value": True,
                                "type": "boolean"
                            },
                            {
                                "name": "result",
                                "value": result,
                                "type": "object"
                            }
                        ]
                    }
                    
                except socket.gaierror as e:
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "success",
                                "value": False,
                                "type": "boolean"
                            },
                            {
                                "name": "result",
                                "value": {
                                    "target": target,
                                    "record_type": record_type,
                                    "error": str(e)
                                },
                                "type": "object"
                            }
                        ]
                    }
                
            elif operation == "check_port":
                # Check if a specific port is open on the target
                port = options.get("port")
                timeout_sec = options.get("timeout", 2)
                
                if not port:
                    return self._error_response("Port parameter is required for check_port operation")
                
                try:
                    port = int(port)
                    if port < 1 or port > 65535:
                        return self._error_response("Port must be between 1 and 65535")
                except ValueError:
                    return self._error_response("Port must be an integer")
                
                # Perform the port check
                try:
                    start_time = time.time()
                    
                    # Create socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout_sec)
                    
                    # Try to connect
                    result = sock.connect_ex((target, port))
                    sock.close()
                    
                    end_time = time.time()
                    
                    port_open = (result == 0)
                    
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "success",
                                "value": True,
                                "type": "boolean"
                            },
                            {
                                "name": "result",
                                "value": {
                                    "target": target,
                                    "port": port,
                                    "open": port_open,
                                    "time_ms": int((end_time - start_time) * 1000)
                                },
                                "type": "object"
                            }
                        ]
                    }
                    
                except Exception as e:
                    return {
                        "status": "success",
                        "outputs": [
                            {
                                "name": "success",
                                "value": False,
                                "type": "boolean"
                            },
                            {
                                "name": "result",
                                "value": {
                                    "target": target,
                                    "port": port,
                                    "error": str(e)
                                },
                                "type": "object"
                            }
                        ]
                    }
                
            elif operation == "local_info":
                # Get local network information
                
                # Get hostname
                hostname = socket.gethostname()
                
                # Get local IP addresses
                local_ips = []
                try:
                    for iface in socket.getaddrinfo(hostname, None):
                        ip = iface[4][0]
                        # Filter out loopback addresses
                        if not ip.startswith("127."):
                            local_ips.append(ip)
                except Exception:
                    pass
                
                # Get default interface
                default_ip = None
                try:
                    # Create a socket that doesn't connect
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    default_ip = s.getsockname()[0]
                    s.close()
                except Exception:
                    pass
                
                result = {
                    "hostname": hostname,
                    "interfaces": local_ips,
                    "default_interface": default_ip
                }
                
                return {
                    "status": "success",
                    "outputs": [
                        {
                            "name": "success",
                            "value": True,
                            "type": "boolean"
                        },
                        {
                            "name": "result",
                            "value": result,
                            "type": "object"
                        }
                    ]
                }
                
            else:
                return self._error_response(f"Unsupported operation: {operation}")
                
        except Exception as e:
            logger.error(f"Network diagnostic error: {e}")
            return self._error_response(f"Network diagnostic failed: {str(e)}")
    
    async def discover_services(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover network services.
        
        Args:
            parameters: Discovery parameters
                - protocol: Protocol to discover (e.g., "http", "ssh", "mdns")
                - network: Network to scan (default: local network)
                - timeout: Scan timeout
        
        Returns:
            List of discovered services
        """
        protocol = parameters.get("protocol", "http")
        network = parameters.get("network")
        timeout = parameters.get("timeout", 5)
        
        # Security check - service discovery should be restricted to local network
        if network and not self._is_private_network(network):
            return self._error_response("Service discovery is restricted to private networks")
        
        # In a real implementation, we would perform actual network scanning
        # For this example, we'll return simulated results
        
        # Simulate discovering various services
        discovered_services = []
        
        if protocol == "http" or protocol == "all":
            discovered_services.extend([
                {
                    "protocol": "http",
                    "host": "192.168.1.10",
                    "port": 80,
                    "name": "Web Server",
                    "details": {
                        "server": "nginx/1.18.0",
                        "title": "Welcome Page"
                    }
                },
                {
                    "protocol": "http",
                    "host": "192.168.1.15",
                    "port": 8080,
                    "name": "Development Server",
                    "details": {
                        "server": "Apache/2.4.41",
                        "title": "Development Portal"
                    }
                }
            ])
        
        if protocol == "ssh" or protocol == "all":
            discovered_services.extend([
                {
                    "protocol": "ssh",
                    "host": "192.168.1.5",
                    "port": 22,
                    "name": "SSH Server",
                    "details": {
                        "version": "OpenSSH_8.2"
                    }
                }
            ])
        
        if protocol == "mdns" or protocol == "all":
            discovered_services.extend([
                {
                    "protocol": "mdns",
                    "host": "printer.local",
                    "ip": "192.168.1.20",
                    "name": "Office Printer",
                    "details": {
                        "device_type": "printer",
                        "model": "HP LaserJet Pro M404n"
                    }
                },
                {
                    "protocol": "mdns",
                    "host": "living-room-tv.local",
                    "ip": "192.168.1.25",
                    "name": "Living Room TV",
                    "details": {
                        "device_type": "media",
                        "model": "Samsung Smart TV"
                    }
                }
            ])
        
        if protocol == "upnp" or protocol == "all":
            discovered_services.extend([
                {
                    "protocol": "upnp",
                    "host": "192.168.1.1",
                    "name": "Wireless Router",
                    "details": {
                        "device_type": "router",
                        "manufacturer": "Linksys",
                        "model": "WRT3200ACM"
                    }
                }
            ])
        
        # Sort by host
        discovered_services.sort(key=lambda s: s.get("host", ""))
        
        return {
            "status": "success",
            "outputs": [
                {
                    "name": "services",
                    "value": discovered_services,
                    "type": "array"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 500,
                "memory_used_mb": 1.0
            }
        }
    
    def _validate_request_security(self, method: str, url: str, headers: Dict[str, str], body: Any = None) -> None:
        """
        Validate a request against security policies.
        
        Args:
            method: Request method
            url: Target URL
            headers: Request headers
            body: Request body
            
        Raises:
            SecurityError: If the request violates security policies
        """
        # Parse URL
        parsed_url = urllib.parse.urlparse(url)
        
        # Check domain restrictions
        domain = parsed_url.netloc
        if ":" in domain:
            domain = domain.split(":")[0]
        
        # Check blocked domains
        blocked_domains = self.security_settings.get("blocked_domains", [])
        for blocked in blocked_domains:
            if self._domain_matches(domain, blocked):
                raise SecurityError(f"Domain {domain} is blocked by policy")
        
        # Check allowed domains if not wildcard
        allowed_domains = self.security_settings.get("allowed_domains", ["*"])
        if "*" not in allowed_domains:
            if not any(self._domain_matches(domain, allowed) for allowed in allowed_domains):
                raise SecurityError(f"Domain {domain} is not in the allowed domains list")
        
        # Resolve domain to IP for IP-based restrictions
        try:
            ip = socket.gethostbyname(domain)
            
            # Check blocked IPs
            blocked_ips = self.security_settings.get("blocked_ips", [])
            for blocked in blocked_ips:
                if self._ip_matches(ip, blocked):
                    raise SecurityError(f"IP {ip} is blocked by policy")
            
            # Check allowed IPs if not wildcard
            allowed_ips = self.security_settings.get("allowed_ips", ["*"])
            if "*" not in allowed_ips:
                if not any(self._ip_matches(ip, allowed) for allowed in allowed_ips):
                    raise SecurityError(f"IP {ip} is not in the allowed IPs list")
                    
        except socket.gaierror:
            # DNS resolution failed
            logger.warning(f"DNS resolution failed for {domain}")
        
        # Check request size limits
        if body:
            body_size = 0
            if isinstance(body, str):
                body_size = len(body.encode('utf-8'))
            elif isinstance(body, bytes):
                body_size = len(body)
            elif isinstance(body, dict) or isinstance(body, list):
                body_size = len(json.dumps(body).encode('utf-8'))
            
            max_size = self.security_settings.get("max_request_size_mb", 10) * 1024 * 1024
            if body_size > max_size:
                raise SecurityError(f"Request body size ({body_size / 1024 / 1024:.2f} MB) exceeds maximum allowed size ({max_size / 1024 / 1024:.2f} MB)")
    
    def _validate_target_security(self, target: str) -> None:
        """
        Validate a target against security policies.
        
        Args:
            target: Target host or IP
            
        Raises:
            SecurityError: If the target violates security policies
        """
        # Determine if target is an IP or domain
        is_ip = self._is_ip_address(target)
        
        if is_ip:
            # Check blocked IPs
            blocked_ips = self.security_settings.get("blocked_ips", [])
            for blocked in blocked_ips:
                if self._ip_matches(target, blocked):
                    raise SecurityError(f"IP {target} is blocked by policy")
            
            # Check allowed IPs if not wildcard
            allowed_ips = self.security_settings.get("allowed_ips", ["*"])
            if "*" not in allowed_ips:
                if not any(self._ip_matches(target, allowed) for allowed in allowed_ips):
                    raise SecurityError(f"IP {target} is not in the allowed IPs list")
        else:
            # Check blocked domains
            blocked_domains = self.security_settings.get("blocked_domains", [])
            for blocked in blocked_domains:
                if self._domain_matches(target, blocked):
                    raise SecurityError(f"Domain {target} is blocked by policy")
            
            # Check allowed domains if not wildcard
            allowed_domains = self.security_settings.get("allowed_domains", ["*"])
            if "*" not in allowed_domains:
                if not any(self._domain_matches(target, allowed) for allowed in allowed_domains):
                    raise SecurityError(f"Domain {target} is not in the allowed domains list")
    
    def _domain_matches(self, domain: str, pattern: str) -> bool:
        """
        Check if a domain matches a pattern.
        
        Args:
            domain: Domain to check
            pattern: Pattern to match against
            
        Returns:
            True if the domain matches the pattern, False otherwise
        """
        if pattern.startswith("*."):
            suffix = pattern[2:]
            return domain.endswith(suffix) and "." in domain
        else:
            return domain == pattern
    
    def _ip_matches(self, ip: str, pattern: str) -> bool:
        """
        Check if an IP matches a pattern.
        
        Args:
            ip: IP to check
            pattern: Pattern to match against (exact IP or CIDR notation)
            
        Returns:
            True if the IP matches the pattern, False otherwise
        """
        if "/" in pattern:
            # CIDR notation
            try:
                # This is a simplified check, in a real implementation we would use a proper IP library
                network, bits = pattern.split("/")
                bits = int(bits)
                
                # Convert IP to integer
                ip_int = self._ip_to_int(ip)
                network_int = self._ip_to_int(network)
                
                # Create mask
                mask = (1 << 32) - (1 << (32 - bits))
                
                # Check if IP is in network
                return (ip_int & mask) == (network_int & mask)
                
            except Exception:
                return False
        else:
            # Exact match
            return ip == pattern
    
    def _ip_to_int(self, ip: str) -> int:
        """
        Convert an IP address to an integer.
        
        Args:
            ip: IP address
            
        Returns:
            Integer representation of the IP
        """
        octets = ip.split(".")
        if len(octets) != 4:
            return 0
        
        result = 0
        for octet in octets:
            result = (result << 8) + int(octet)
        
        return result
    
    def _is_ip_address(self, host: str) -> bool:
        """
        Check if a host is an IP address.
        
        Args:
            host: Host to check
            
        Returns:
            True if the host is an IP address, False otherwise
        """
        try:
            octets = host.split(".")
            if len(octets) != 4:
                return False
            
            for octet in octets:
                num = int(octet)
                if num < 0 or num > 255:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _is_private_network(self, network: str) -> bool:
        """
        Check if a network is a private network.
        
        Args:
            network: Network to check
            
        Returns:
            True if the network is private, False otherwise
        """
        if "/" in network:
            # CIDR notation
            ip = network.split("/")[0]
        else:
            ip = network
        
        # Check if IP is in private ranges
        if ip.startswith("10.") or ip.startswith("192.168."):
            return True
        
        if ip.startswith("172."):
            try:
                second_octet = int(ip.split(".")[1])
                return 16 <= second_octet <= 31
            except Exception:
                return False
        
        return False
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
        
        Returns:
            Error response dictionary
        """
        logger.error(f"Network interface error: {message}")
        return {
            "status": "error",
            "error": message,
            "outputs": [
                {
                    "name": "error",
                    "value": message,
                    "type": "string"
                }
            ],
            "performance_metrics": {
                "execution_time_ms": 1,
                "memory_used_mb": 0.1
            }
        }
    
    async def suspend(self) -> Dict[str, Any]:
        """
        Prepare for suspension by saving state.
        
        Returns:
            Suspension result with saved state
        """
        try:
            # Prepare state for suspension
            state = {
                "dns_cache": self.dns_cache,
                "active_websockets": self.active_websockets,
                "security_settings": self.security_settings,
                "network_settings": self.network_settings
            }
            
            # Close active connections
            for connection_id in list(self.active_websockets.keys()):
                # In a real implementation, close the actual WebSocket connections
                logger.debug(f"Closing WebSocket connection: {connection_id}")
                self.active_websockets[connection_id]["status"] = "suspended"
            
            result = {
                "status": "success",
                "state": "suspended",
                "saved_state": state
            }
            
            logger.info("Network interface cell suspended")
            return result
            
        except Exception as e:
            logger.error(f"Error during suspension: {e}")
            return {
                "status": "error",
                "state": "error",
                "error": f"Suspension failed: {str(e)}"
            }
    
    async def resume(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume from suspension with saved state.
        
        Args:
            parameters: Resume parameters including saved state
        
        Returns:
            Resume result
        """
        try:
            # Restore state if provided
            if "saved_state" in parameters:
                saved_state = parameters["saved_state"]
                
                if "dns_cache" in saved_state:
                    self.dns_cache = saved_state["dns_cache"]
                
                if "security_settings" in saved_state:
                    self.security_settings.update(saved_state["security_settings"])
                
                if "network_settings" in saved_state:
                    self.network_settings.update(saved_state["network_settings"])
                
                if "active_websockets" in saved_state:
                    # In a real implementation, reconnect WebSockets
                    reconnected_count = 0
                    for ws_id, ws_info in saved_state["active_websockets"].items():
                        if ws_info["status"] == "suspended":
                            # Here we would reconnect
                            logger.debug(f"Reconnecting WebSocket: {ws_id}")
                            ws_info["status"] = "connecting"
                            reconnected_count += 1
                    
                    # Don't actually reconnect for this example, just restore the state
                    self.active_websockets = saved_state["active_websockets"]
                    logger.info(f"Restored {reconnected_count} WebSocket connections")
                
                logger.info("Network interface cell resumed with saved state")
            else:
                logger.warning("Resumed without saved state")
            
            return {
                "status": "success",
                "state": "active"
            }
            
        except Exception as e:
            logger.error(f"Error during resume: {e}")
            return {
                "status": "error",
                "state": "error",
                "error": f"Resume failed: {str(e)}"
            }
    
    async def release(self) -> Dict[str, Any]:
        """
        Prepare for release.
        
        Returns:
            Release result
        """
        try:
            # Close all connections
            for connection_id in list(self.active_websockets.keys()):
                # In a real implementation, close the actual WebSocket connections
                logger.debug(f"Closing WebSocket connection: {connection_id}")
                # Close action would happen here
            
            # Clear state
            self.active_websockets = {}
            self.dns_cache = {}
            self.connection_pools = {}
            
            logger.info("Network interface cell released")
            
            return {
                "status": "success",
                "state": "released"
            }
            
        except Exception as e:
            logger.error(f"Error during release: {e}")
            return {
                "status": "error",
                "state": "error",
                "error": f"Release failed: {str(e)}"
            }

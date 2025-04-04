# Assembler API Specification

## Overview

The Assembler API provides interfaces for interacting with the QCC Assembler, the core orchestration component of the Quantum Cellular Computing system. This API enables applications to submit user intents, manage solutions, query system status, and configure assembler behavior.

## API Endpoints

The Assembler API is organized into four main categories:

1. User Intent API
2. Solution Management API
3. System Status API
4. Configuration API

Each category addresses a specific aspect of assembler functionality.

## 1. User Intent API

The User Intent API allows applications to submit user requests for interpretation and fulfillment by the QCC system.

### Base URL

```
https://{assembler-host}/api/v1/intent
```

### Endpoints

#### Submit Intent

Submits a user intent for processing.

**HTTP Method**: POST  
**Path**: `/`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "user_request": "string",      // Natural language description of user need
  "context": {                   // Optional contextual information
    "device_info": {             // Information about the device
      "platform": "string",
      "memory_gb": "number",
      "cpu_cores": "number",
      "gpu_available": "boolean"
    },
    "preferences": {             // User preferences
      "key": "value"
    },
    "environment": {             // Environmental context
      "key": "value"
    }
  },
  "priority": "number",          // Optional priority level (1-10)
  "timeout_ms": "number"         // Optional timeout in milliseconds
}
```

**Response**:

```json
{
  "solution_id": "string",       // Unique identifier for the assembled solution
  "status": "string",            // Current status (assembling, active, error)
  "estimated_completion_ms": "number", // Estimated time until solution is ready
  "capabilities": [              // List of capabilities being assembled
    "string"
  ],
  "error": {                     // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 202 Accepted: Intent accepted for processing
- 400 Bad Request: Invalid intent format
- 401 Unauthorized: Authentication failed
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

**Example**:

```
POST /api/v1/intent/
Content-Type: application/json
Authorization: Bearer {token}

{
  "user_request": "Create a presentation about sustainable energy with 10 slides",
  "context": {
    "device_info": {
      "platform": "windows",
      "memory_gb": 16,
      "cpu_cores": 8,
      "gpu_available": true
    },
    "preferences": {
      "theme": "modern",
      "color_scheme": "blue"
    }
  },
  "priority": 5,
  "timeout_ms": 30000
}
```

Response:

```json
{
  "solution_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "assembling",
  "estimated_completion_ms": 5000,
  "capabilities": [
    "presentation_creation",
    "content_research",
    "image_selection",
    "layout_design"
  ]
}
```

#### Check Intent Status

Checks the status of a previously submitted intent.

**HTTP Method**: GET  
**Path**: `/{intent_id}`  
**Parameters**:
- `intent_id` (path): The ID of the submitted intent

**Response**:

```json
{
  "intent_id": "string",
  "solution_id": "string",
  "status": "string",       // assembling, active, completed, error
  "progress": "number",     // 0-100 completion percentage
  "created_at": "string",   // ISO timestamp
  "updated_at": "string"    // ISO timestamp
}
```

**Status Codes**:
- 200 OK: Status returned successfully
- 404 Not Found: Intent ID not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Cancel Intent

Cancels a previously submitted intent.

**HTTP Method**: DELETE  
**Path**: `/{intent_id}`  
**Parameters**:
- `intent_id` (path): The ID of the submitted intent

**Response**:

```json
{
  "intent_id": "string",
  "status": "string",       // cancelling, cancelled
  "message": "string"
}
```

**Status Codes**:
- 200 OK: Intent cancelled successfully
- 202 Accepted: Cancellation in progress
- 404 Not Found: Intent ID not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## 2. Solution Management API

The Solution Management API provides methods to manage active solutions assembled by the QCC system.

### Base URL

```
https://{assembler-host}/api/v1/solutions
```

### Endpoints

#### List Active Solutions

Returns a list of currently active solutions.

**HTTP Method**: GET  
**Path**: `/`  
**Query Parameters**:
- `limit` (optional): Maximum number of solutions to return
- `offset` (optional): Offset for pagination
- `status` (optional): Filter by solution status

**Response**:

```json
{
  "solutions": [
    {
      "solution_id": "string",
      "created_at": "string",     // ISO timestamp
      "status": "string",         // active, suspended, error
      "intent_summary": "string", // Brief description of the intent
      "cell_count": "number",     // Number of cells in the solution
      "resource_usage": {
        "memory_mb": "number",
        "cpu_percent": "number"
      }
    }
  ],
  "total_count": "number",
  "limit": "number",
  "offset": "number"
}
```

**Status Codes**:
- 200 OK: Solutions returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Solution Details

Returns detailed information about a specific solution.

**HTTP Method**: GET  
**Path**: `/{solution_id}`  
**Parameters**:
- `solution_id` (path): The ID of the solution

**Response**:

```json
{
  "solution_id": "string",
  "status": "string",            // active, suspended, error
  "created_at": "string",        // ISO timestamp
  "intent": {
    "user_request": "string",
    "interpreted_intent": "string",
    "context": {}
  },
  "cells": [
    {
      "cell_id": "string",
      "capability": "string",
      "provider": "string",
      "status": "string",
      "resource_usage": {
        "memory_mb": "number",
        "cpu_percent": "number"
      }
    }
  ],
  "connection_map": {            // How cells are connected
    "cell_id": ["connected_cell_id1", "connected_cell_id2"]
  },
  "performance_metrics": {
    "assembly_time_ms": "number",
    "total_usage_time_ms": "number",
    "memory_peak_mb": "number",
    "cpu_usage_avg": "number"
  },
  "quantum_signature": "string"  // Signature for this solution
}
```

**Status Codes**:
- 200 OK: Solution details returned successfully
- 404 Not Found: Solution ID not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Suspend Solution

Temporarily suspends an active solution.

**HTTP Method**: POST  
**Path**: `/{solution_id}/suspend`  
**Parameters**:
- `solution_id` (path): The ID of the solution

**Response**:

```json
{
  "solution_id": "string",
  "status": "string",       // suspending, suspended
  "message": "string"
}
```

**Status Codes**:
- 200 OK: Solution suspended successfully
- 202 Accepted: Suspension in progress
- 404 Not Found: Solution ID not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Resume Solution

Resumes a suspended solution.

**HTTP Method**: POST  
**Path**: `/{solution_id}/resume`  
**Parameters**:
- `solution_id` (path): The ID of the solution

**Response**:

```json
{
  "solution_id": "string",
  "status": "string",       // resuming, active
  "message": "string"
}
```

**Status Codes**:
- 200 OK: Solution resumed successfully
- 202 Accepted: Resume in progress
- 404 Not Found: Solution ID not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Release Solution

Releases a solution, freeing its resources.

**HTTP Method**: DELETE  
**Path**: `/{solution_id}`  
**Parameters**:
- `solution_id` (path): The ID of the solution

**Response**:

```json
{
  "solution_id": "string",
  "status": "string",       // releasing, released
  "message": "string"
}
```

**Status Codes**:
- 200 OK: Solution released successfully
- 202 Accepted: Release in progress
- 404 Not Found: Solution ID not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## 3. System Status API

The System Status API provides information about the current state and performance of the QCC Assembler.

### Base URL

```
https://{assembler-host}/api/v1/status
```

### Endpoints

#### Get System Status

Returns the current status of the assembler.

**HTTP Method**: GET  
**Path**: `/`

**Response**:

```json
{
  "assembler_id": "string",
  "status": "string",           // active, starting, stopping, error
  "uptime_seconds": "number",
  "active_solutions": "number",
  "cached_cells": "number",
  "total_assemblies": "number",
  "total_cells_requested": "number",
  "version": "string",
  "health": {
    "cpu_usage_percent": "number",
    "memory_usage_mb": "number",
    "disk_usage_mb": "number",
    "network_usage_mbps": "number"
  }
}
```

**Status Codes**:
- 200 OK: Status returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Resource Usage

Returns detailed resource usage information.

**HTTP Method**: GET  
**Path**: `/resources`

**Response**:

```json
{
  "timestamp": "string",       // ISO timestamp
  "cpu": {
    "usage_percent": "number",
    "core_count": "number",
    "per_core": [
      {
        "core_id": "number",
        "usage_percent": "number"
      }
    ]
  },
  "memory": {
    "total_mb": "number",
    "used_mb": "number",
    "free_mb": "number",
    "cached_mb": "number"
  },
  "disk": {
    "total_mb": "number",
    "used_mb": "number",
    "free_mb": "number",
    "read_mbps": "number",
    "write_mbps": "number"
  },
  "network": {
    "incoming_mbps": "number",
    "outgoing_mbps": "number",
    "active_connections": "number"
  }
}
```

**Status Codes**:
- 200 OK: Resource usage returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Provider Statistics

Returns statistics about cell providers.

**HTTP Method**: GET  
**Path**: `/providers`

**Response**:

```json
{
  "providers": [
    {
      "provider_url": "string",
      "status": "string",           // active, inactive, error
      "cells_requested": "number",
      "average_response_time_ms": "number",
      "success_rate_percent": "number",
      "last_error": {
        "timestamp": "string",
        "code": "string",
        "message": "string"
      }
    }
  ]
}
```

**Status Codes**:
- 200 OK: Provider statistics returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Health Check

Performs a health check on the assembler.

**HTTP Method**: GET  
**Path**: `/health`

**Response**:

```json
{
  "status": "string",           // healthy, warning, critical
  "message": "string",
  "components": [
    {
      "name": "string",
      "status": "string",
      "message": "string"
    }
  ],
  "timestamp": "string"        // ISO timestamp
}
```

**Status Codes**:
- 200 OK: Healthy
- 207 Multi-Status: Some components unhealthy
- 503 Service Unavailable: Critical components unhealthy
- 500 Internal Server Error: Server error

## 4. Configuration API

The Configuration API enables customization of assembler behavior and preferences.

### Base URL

```
https://{assembler-host}/api/v1/config
```

### Endpoints

#### Get Current Configuration

Returns the current assembler configuration.

**HTTP Method**: GET  
**Path**: `/`

**Response**:

```json
{
  "general": {
    "max_concurrent_solutions": "number",
    "max_cell_cache_size_mb": "number",
    "default_request_timeout_ms": "number"
  },
  "security": {
    "security_level": "string",     // standard, high, maximum
    "verification_mode": "string",  // standard, strict
    "allowed_providers": [
      "string"
    ]
  },
  "performance": {
    "resource_allocation_strategy": "string",  // balanced, memory_optimized, cpu_optimized
    "prefetch_enabled": "boolean",
    "prefetch_threshold": "number"
  },
  "providers": [
    {
      "url": "string",
      "priority": "number",
      "capabilities": [
        "string"
      ]
    }
  ],
  "user_preferences": {
    "default_language": "string",
    "timezone": "string",
    "theme": "string",
    "key": "value"
  }
}
```

**Status Codes**:
- 200 OK: Configuration returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Update Configuration

Updates the assembler configuration.

**HTTP Method**: PATCH  
**Path**: `/`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "general": {
    "max_concurrent_solutions": "number",
    "max_cell_cache_size_mb": "number",
    "default_request_timeout_ms": "number"
  },
  "security": {
    "security_level": "string",
    "verification_mode": "string",
    "allowed_providers": [
      "string"
    ]
  },
  "performance": {
    "resource_allocation_strategy": "string",
    "prefetch_enabled": "boolean",
    "prefetch_threshold": "number"
  },
  "providers": [
    {
      "url": "string",
      "priority": "number",
      "capabilities": [
        "string"
      ]
    }
  ],
  "user_preferences": {
    "default_language": "string",
    "timezone": "string",
    "theme": "string",
    "key": "value"
  }
}
```

**Response**:

```json
{
  "status": "string",          // success, partial_success, error
  "message": "string",
  "applied_changes": [
    "string"
  ],
  "rejected_changes": [
    {
      "path": "string",
      "reason": "string"
    }
  ]
}
```

**Status Codes**:
- 200 OK: Configuration updated successfully
- 207 Multi-Status: Some configuration changes applied
- 400 Bad Request: Invalid configuration
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Reset Configuration

Resets the assembler configuration to defaults.

**HTTP Method**: POST  
**Path**: `/reset`

**Response**:

```json
{
  "status": "string",          // success, error
  "message": "string"
}
```

**Status Codes**:
- 200 OK: Configuration reset successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Provider Configuration

Returns the configuration for cell providers.

**HTTP Method**: GET  
**Path**: `/providers`

**Response**:

```json
{
  "providers": [
    {
      "url": "string",
      "priority": "number",
      "enabled": "boolean",
      "capabilities": [
        "string"
      ],
      "auth_method": "string",
      "timeout_ms": "number",
      "retry_policy": {
        "max_retries": "number",
        "backoff_factor": "number"
      }
    }
  ],
  "default_timeout_ms": "number",
  "default_retry_policy": {
    "max_retries": "number",
    "backoff_factor": "number"
  }
}
```

**Status Codes**:
- 200 OK: Provider configuration returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Update Provider Configuration

Updates the configuration for cell providers.

**HTTP Method**: PATCH  
**Path**: `/providers`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "providers": [
    {
      "url": "string",
      "priority": "number",
      "enabled": "boolean",
      "capabilities": [
        "string"
      ],
      "auth_method": "string",
      "timeout_ms": "number",
      "retry_policy": {
        "max_retries": "number",
        "backoff_factor": "number"
      }
    }
  ],
  "default_timeout_ms": "number",
  "default_retry_policy": {
    "max_retries": "number",
    "backoff_factor": "number"
  }
}
```

**Response**:

```json
{
  "status": "string",          // success, partial_success, error
  "message": "string",
  "applied_changes": [
    "string"
  ],
  "rejected_changes": [
    {
      "path": "string",
      "reason": "string"
    }
  ]
}
```

**Status Codes**:
- 200 OK: Provider configuration updated successfully
- 207 Multi-Status: Some configuration changes applied
- 400 Bad Request: Invalid configuration
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## Error Codes

| Code | Description |
|------|-------------|
| AUTH_001 | Invalid authentication token |
| AUTH_002 | Token expired |
| AUTH_003 | Insufficient permissions |
| INTENT_001 | Invalid intent format |
| INTENT_002 | Intent processing timeout |
| INTENT_003 | Required capability unavailable |
| SOLUTION_001 | Solution not found |
| SOLUTION_002 | Solution already released |
| SOLUTION_003 | Maximum concurrent solutions reached |
| PROVIDER_001 | Provider unavailable |
| PROVIDER_002 | Provider returned invalid cell |
| SYSTEM_001 | Assembler overloaded |
| SYSTEM_002 | Resource allocation failed |
| CONFIG_001 | Invalid configuration format |
| CONFIG_002 | Configuration update failed |

## Webhooks

The Assembler API supports webhooks for asynchronous notifications of events.

### Webhook Registration

**HTTP Method**: POST  
**Path**: `/api/v1/webhooks`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "url": "string",              // Webhook destination URL
  "events": [                   // Events to subscribe to
    "solution.created",
    "solution.completed",
    "solution.error",
    "cell.error"
  ],
  "secret": "string"           // Secret for webhook signature
}
```

**Response**:

```json
{
  "webhook_id": "string",
  "status": "string",
  "message": "string"
}
```

### Webhook Payload Format

When an event occurs, the assembler sends a POST request to the registered webhook URL with this payload:

```json
{
  "event_type": "string",          // Type of event
  "timestamp": "string",           // ISO timestamp
  "assembler_id": "string",        // ID of the assembler
  "data": {},                      // Event-specific data
  "signature": "string"            // HMAC signature for verification
}
```

## SDK Support

The Assembler API is available in the following language SDKs:

- Python: `pip install qcc-assembler-client`
- JavaScript: `npm install qcc-assembler-client`
- Java: Maven dependency `ai.cellcomputing:qcc-assembler-client:1.0.0`
- C#: NuGet package `QCC.Assembler.Client`
- Go: `go get github.com/cellcomputing/qcc-assembler-client`

## Conclusion

This document specifies the Assembler API for the QCC system. The API provides a comprehensive interface for interacting with the assembler, enabling applications to submit user intents, manage solutions, query system status, and configure assembler behavior.

For examples and sample code, refer to the Assembler API Tutorials document.

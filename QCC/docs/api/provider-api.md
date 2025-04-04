# Provider API Specification

## Overview

The Provider API defines the interfaces for cell provider services within the Quantum Cellular Computing (QCC) system. Cell providers act as repositories of cells, responding to requests from assemblers and managing cell lifecycle. This specification outlines the standard protocols that all provider services must implement.

## Provider Role

Cell providers serve several essential functions in the QCC ecosystem:

1. **Cell Repository**: Store and maintain libraries of cells with different capabilities.
2. **Cell Delivery**: Deliver cells to assemblers in response to capability requests.
3. **Security Verification**: Ensure cells are secure and authentic.
4. **Cell Updates**: Manage cell versioning and updates.
5. **Analytics**: Collect anonymous usage data to improve cell offerings.

## API Categories

The Provider API is organized into several categories:

1. Cell Request API
2. Cell Repository Management API
3. Provider Discovery API
4. Usage Analytics API
5. Provider Federation API

## 1. Cell Request API

The Cell Request API defines how assemblers request cells from providers.

### Base URL

```
https://{provider-host}/api/v1/cells
```

### Endpoints

#### Request Cell by Capability

Requests a cell that provides a specific capability.

**HTTP Method**: POST  
**Path**: `/request`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "request_id": "string",            // Unique request identifier
  "capability": "string",            // Required capability
  "quantum_signature": "string",     // Quantum signature for security
  "context": {                       // Contextual information
    "device_info": {
      "platform": "string",
      "memory_gb": "number",
      "cpu_cores": "number",
      "gpu_available": "boolean"
    },
    "environment": {},               // Environment-specific context
    "intent_context": {}             // Intent-specific context
  },
  "preferences": {                   // Cell preference criteria
    "version_constraints": "string", // Version requirements (e.g., ">=1.0.0")
    "optimization_priority": "string", // memory, speed, battery
    "security_level": "string"       // standard, high, maximum
  }
}
```

**Response**:

```json
{
  "request_id": "string",            // Echo of request ID
  "status": "string",                // success, pending, not_found, error
  "cell": {                          // Present if status is "success"
    "cell_id": "string",             // Unique cell identifier
    "cell_type": "string",           // Type of cell
    "capability": "string",          // Primary capability
    "version": "string",             // Cell version
    "signature": "string",           // Digital signature of cell
    "packaging_format": "string",    // wasm, container, etc.
    "size_bytes": "number",          // Size of cell
    "download_url": "string",        // URL to download cell
    "metadata": {                    // Additional cell metadata
      "provider": "string",
      "created_at": "string",        // ISO timestamp
      "description": "string",
      "security_rating": "string",
      "performance_characteristics": {
        "typical_memory_mb": "number",
        "typical_startup_ms": "number"
      },
      "capabilities": [              // All capabilities of this cell
        {
          "name": "string",
          "version": "string"
        }
      ],
      "dependencies": [              // Other cell dependencies
        {
          "capability": "string",
          "version_constraint": "string"
        }
      ]
    }
  },
  "estimated_wait_time_ms": "number", // If status is "pending"
  "alternatives": [                  // If requested cell not available
    {
      "capability": "string",
      "cell_type": "string",
      "version": "string",
      "compatibility_notes": "string"
    }
  ],
  "error": {                        // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 200 OK: Cell request processed
- 202 Accepted: Request pending, check back later
- 404 Not Found: No suitable cell found
- 401 Unauthorized: Authentication failed
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

#### Request Specific Cell Type

Requests a specific cell type.

**HTTP Method**: POST  
**Path**: `/request/specific`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "request_id": "string",            // Unique request identifier
  "cell_type": "string",             // Requested cell type
  "version": "string",               // Specific version or constraint
  "quantum_signature": "string",     // Quantum signature for security
  "context": {                       // Contextual information
    "device_info": {
      "platform": "string",
      "memory_gb": "number",
      "cpu_cores": "number",
      "gpu_available": "boolean"
    },
    "environment": {},               // Environment-specific context
    "intent_context": {}             // Intent-specific context
  }
}
```

**Response**: Same as above

#### Check Request Status

Checks the status of a pending cell request.

**HTTP Method**: GET  
**Path**: `/request/{request_id}`  
**Parameters**:
- `request_id` (path): The ID of the previous request

**Response**: Same as above

#### Cancel Request

Cancels a pending cell request.

**HTTP Method**: DELETE  
**Path**: `/request/{request_id}`  
**Parameters**:
- `request_id` (path): The ID of the request to cancel

**Response**:

```json
{
  "request_id": "string",
  "status": "string",               // cancelled, already_delivered, not_found
  "message": "string"
}
```

**Status Codes**:
- 200 OK: Request cancelled successfully
- 404 Not Found: Request ID not found
- 409 Conflict: Request already fulfilled
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## 2. Cell Repository Management API

The Cell Repository Management API defines how authorized administrators manage cells in the provider repository.

### Base URL

```
https://{provider-host}/api/v1/repository
```

### Endpoints

#### List Available Cells

Returns a list of cells available in the repository.

**HTTP Method**: GET  
**Path**: `/cells`  
**Query Parameters**:
- `capability` (optional): Filter by capability
- `version` (optional): Filter by version
- `limit` (optional): Maximum number of cells to return
- `offset` (optional): Offset for pagination

**Response**:

```json
{
  "cells": [
    {
      "cell_type": "string",
      "capabilities": [
        {
          "name": "string",
          "version": "string"
        }
      ],
      "versions": [
        {
          "version": "string",
          "created_at": "string",  // ISO timestamp
          "status": "string"       // active, deprecated, in_testing
        }
      ],
      "description": "string",
      "tags": ["string"]
    }
  ],
  "total_count": "number",
  "limit": "number",
  "offset": "number"
}
```

**Status Codes**:
- 200 OK: Cells returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Cell Details

Returns detailed information about a specific cell.

**HTTP Method**: GET  
**Path**: `/cells/{cell_type}`  
**Parameters**:
- `cell_type` (path): The cell type
- `version` (query, optional): Specific version

**Response**:

```json
{
  "cell_type": "string",
  "version": "string",
  "description": "string",
  "capabilities": [
    {
      "name": "string",
      "version": "string",
      "description": "string",
      "parameters": [
        {
          "name": "string",
          "type": "string",
          "required": "boolean",
          "default": "any",
          "description": "string"
        }
      ],
      "inputs": [
        {
          "name": "string",
          "type": "string",
          "format": "string",
          "description": "string"
        }
      ],
      "outputs": [
        {
          "name": "string",
          "type": "string",
          "format": "string",
          "description": "string"
        }
      ]
    }
  ],
  "dependencies": [
    {
      "capability": "string",
      "version_constraint": "string"
    }
  ],
  "metadata": {
    "created_at": "string",         // ISO timestamp
    "created_by": "string",
    "updated_at": "string",         // ISO timestamp
    "size_bytes": "number",
    "license": "string",
    "documentation_url": "string",
    "repository_url": "string",
    "issue_tracker_url": "string"
  },
  "security": {
    "signature_algorithm": "string",
    "signature": "string",
    "security_rating": "string",
    "vulnerabilities": [
      {
        "id": "string",
        "severity": "string",
        "description": "string",
        "mitigated": "boolean"
      }
    ],
    "last_security_audit": "string" // ISO timestamp
  },
  "performance": {
    "typical_memory_mb": "number",
    "typical_startup_ms": "number",
    "benchmark_results": {}
  },
  "statistics": {
    "total_requests": "number",
    "active_deployments": "number",
    "average_rating": "number"
  }
}
```

**Status Codes**:
- 200 OK: Cell details returned successfully
- 404 Not Found: Cell not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Register New Cell

Registers a new cell in the repository.

**HTTP Method**: POST  
**Path**: `/cells`  
**Content-Type**: multipart/form-data

**Request Body**:
- `metadata` (JSON): Cell metadata in the format shown in Get Cell Details
- `cell_package` (file): The cell package file

**Response**:

```json
{
  "status": "string",              // success, validation_error, error
  "cell_type": "string",
  "version": "string",
  "message": "string",
  "validation_results": {          // If status is "validation_error"
    "issues": [
      {
        "severity": "string",      // error, warning
        "code": "string",
        "message": "string",
        "location": "string"
      }
    ],
    "passed_checks": ["string"]
  },
  "error": {                      // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 201 Created: Cell registered successfully
- 400 Bad Request: Invalid cell package or metadata
- 401 Unauthorized: Authentication failed
- 409 Conflict: Cell already exists
- 500 Internal Server Error: Server error

#### Update Cell

Updates an existing cell in the repository.

**HTTP Method**: PUT  
**Path**: `/cells/{cell_type}`  
**Parameters**:
- `cell_type` (path): The cell type to update
**Content-Type**: multipart/form-data

**Request Body**:
- `metadata` (JSON): Updated cell metadata
- `cell_package` (file, optional): New cell package file
- `version` (string): New version

**Response**: Same as Register New Cell

**Status Codes**:
- 200 OK: Cell updated successfully
- 404 Not Found: Cell not found
- 400 Bad Request: Invalid cell package or metadata
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Delete Cell

Removes a cell from the repository.

**HTTP Method**: DELETE  
**Path**: `/cells/{cell_type}/{version}`  
**Parameters**:
- `cell_type` (path): The cell type to delete
- `version` (path): The version to delete

**Response**:

```json
{
  "status": "string",              // success, error
  "message": "string",
  "error": {                      // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 200 OK: Cell deleted successfully
- 404 Not Found: Cell not found
- 401 Unauthorized: Authentication failed
- 403 Forbidden: Cell in use and cannot be deleted
- 500 Internal Server Error: Server error

#### Cell Validation

Validates a cell package without registering it.

**HTTP Method**: POST  
**Path**: `/validate`  
**Content-Type**: multipart/form-data

**Request Body**:
- `metadata` (JSON): Cell metadata
- `cell_package` (file): The cell package file

**Response**:

```json
{
  "status": "string",              // valid, invalid
  "validation_results": {
    "issues": [
      {
        "severity": "string",      // error, warning
        "code": "string",
        "message": "string",
        "location": "string"
      }
    ],
    "passed_checks": ["string"]
  }
}
```

**Status Codes**:
- 200 OK: Validation completed
- 400 Bad Request: Invalid input
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## 3. Provider Discovery API

The Provider Discovery API allows assemblers to discover and query provider capabilities.

### Base URL

```
https://{provider-host}/api/v1/discovery
```

### Endpoints

#### Get Provider Information

Returns basic information about the provider.

**HTTP Method**: GET  
**Path**: `/info`

**Response**:

```json
{
  "provider_id": "string",
  "name": "string",
  "description": "string",
  "api_version": "string",
  "capabilities": [
    {
      "name": "string",
      "versions": ["string"]
    }
  ],
  "cell_count": "number",
  "status": "string",               // active, maintenance, limited
  "documentation_url": "string",
  "contact_info": {
    "website": "string",
    "email": "string",
    "support_url": "string"
  },
  "federation_status": {
    "federated": "boolean",
    "federation_partners": [
      {
        "provider_id": "string",
        "name": "string",
        "url": "string"
      }
    ]
  },
  "service_level": {
    "uptime_target_percent": "number",
    "response_time_sla_ms": "number"
  }
}
```

**Status Codes**:
- 200 OK: Information returned successfully
- 500 Internal Server Error: Server error

#### Search Capabilities

Searches for providers that offer specific capabilities.

**HTTP Method**: GET  
**Path**: `/capabilities`  
**Query Parameters**:
- `capability` (required): The capability to search for
- `version` (optional): Version constraint
- `include_details` (optional): Whether to include detailed information

**Response**:

```json
{
  "capabilities": [
    {
      "name": "string",
      "versions": ["string"],
      "cell_types": [
        {
          "cell_type": "string",
          "version": "string",
          "description": "string"
        }
      ],
      "documentation_url": "string"
    }
  ]
}
```

**Status Codes**:
- 200 OK: Search results returned
- 400 Bad Request: Invalid search parameters
- 500 Internal Server Error: Server error

#### Get Health Status

Returns the health status of the provider service.

**HTTP Method**: GET  
**Path**: `/health`

**Response**:

```json
{
  "status": "string",               // healthy, degraded, maintenance, offline
  "message": "string",
  "components": [
    {
      "name": "string",
      "status": "string",
      "message": "string"
    }
  ],
  "metrics": {
    "current_request_rate": "number",
    "average_response_time_ms": "number",
    "success_rate_percent": "number"
  },
  "scheduled_maintenance": [
    {
      "start_time": "string",      // ISO timestamp
      "end_time": "string",        // ISO timestamp
      "description": "string"
    }
  ],
  "timestamp": "string"            // ISO timestamp
}
```

**Status Codes**:
- 200 OK: Health status returned
- 500 Internal Server Error: Server error

## 4. Usage Analytics API

The Usage Analytics API enables providers to collect anonymous usage data for cells.

### Base URL

```
https://{provider-host}/api/v1/analytics
```

### Endpoints

#### Submit Cell Usage Report

Submits an anonymous report of cell usage.

**HTTP Method**: POST  
**Path**: `/usage`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "report_id": "string",             // Unique report identifier
  "quantum_signature": "string",     // Quantum signature for anonymity
  "cell_type": "string",
  "version": "string",
  "usage_metrics": {
    "activation_count": "number",
    "total_active_time_ms": "number",
    "peak_memory_mb": "number",
    "average_cpu_percent": "number",
    "capabilities_used": [
      {
        "capability": "string",
        "invocation_count": "number"
      }
    ],
    "error_count": "number"
  },
  "performance_metrics": {
    "initialization_time_ms": "number",
    "response_times_ms": {           // Percentiles
      "p50": "number",
      "p90": "number",
      "p99": "number"
    }
  },
  "environment_summary": {
    "platform": "string",
    "platform_version": "string",
    "memory_gb": "number",
    "cpu_cores": "number",
    "gpu_available": "boolean"
  },
  "timestamp": "string"              // ISO timestamp
}
```

**Response**:

```json
{
  "status": "string",                // success, error
  "report_id": "string",
  "message": "string",
  "error": {                        // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 202 Accepted: Report accepted
- 400 Bad Request: Invalid report format
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Submit Error Report

Submits an anonymous error report.

**HTTP Method**: POST  
**Path**: `/errors`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "report_id": "string",             // Unique report identifier
  "quantum_signature": "string",     // Quantum signature for anonymity
  "cell_type": "string",
  "version": "string",
  "error_type": "string",            // initialization, execution, memory, etc.
  "error_code": "string",
  "error_message": "string",
  "stack_trace": "string",           // Anonymized stack trace
  "related_capabilities": ["string"],
  "environment_summary": {
    "platform": "string",
    "platform_version": "string",
    "memory_gb": "number",
    "cpu_cores": "number",
    "gpu_available": "boolean"
  },
  "context": {                       // Anonymized context information
    "active_cells": "number",
    "system_load": "number",
    "memory_pressure": "number"
  },
  "timestamp": "string"              // ISO timestamp
}
```

**Response**:

```json
{
  "status": "string",                // success, error
  "report_id": "string",
  "known_issue": "boolean",          // Whether this is a known issue
  "issue_id": "string",              // If known_issue is true
  "resolution_url": "string",        // If a resolution is available
  "message": "string",
  "error": {                        // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 202 Accepted: Report accepted
- 400 Bad Request: Invalid report format
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Get Analytics Overview

Returns aggregated analytics information for providers.

**HTTP Method**: GET  
**Path**: `/overview`  
**Query Parameters**:
- `cell_type` (optional): Filter by cell type
- `version` (optional): Filter by version
- `time_range` (optional): Time range for analytics (e.g., "24h", "7d", "30d")

**Response**:

```json
{
  "cell_usage": [
    {
      "cell_type": "string",
      "version": "string",
      "total_requests": "number",
      "unique_quantum_signatures": "number",
      "average_usage_time_ms": "number",
      "error_rate_percent": "number",
      "top_capabilities": [
        {
          "capability": "string",
          "usage_percent": "number"
        }
      ],
      "platform_distribution": {
        "platform_name": "number"   // Percentage of usage
      }
    }
  ],
  "system_metrics": {
    "total_requests": "number",
    "average_response_time_ms": "number",
    "error_rate_percent": "number",
    "peak_requests_per_second": "number"
  },
  "time_range": {
    "start": "string",              // ISO timestamp
    "end": "string"                 // ISO timestamp
  }
}
```

**Status Codes**:
- 200 OK: Analytics returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## 5. Provider Federation API

The Provider Federation API allows providers to collaborate and forward requests.

### Base URL

```
https://{provider-host}/api/v1/federation
```

### Endpoints

#### Federation Status

Returns the federation status of the provider.

**HTTP Method**: GET  
**Path**: `/status`

**Response**:

```json
{
  "federation_enabled": "boolean",
  "federation_id": "string",
  "federation_name": "string",
  "federation_partners": [
    {
      "provider_id": "string",
      "name": "string",
      "url": "string",
      "capabilities": [
        {
          "name": "string",
          "versions": ["string"]
        }
      ],
      "status": "string",           // active, inactive, limited
      "trust_level": "string"       // trusted, limited, untrusted
    }
  ],
  "federation_policies": {
    "auto_forward": "boolean",
    "capability_sharing": "boolean",
    "analytics_sharing": "boolean"
  }
}
```

**Status Codes**:
- 200 OK: Status returned successfully
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

#### Forward Request

Forwards a cell request to a federation partner.

**HTTP Method**: POST  
**Path**: `/forward`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "request_id": "string",
  "target_provider_id": "string",
  "original_request": {},           // Original cell request
  "reason": "string",               // Why the request is being forwarded
  "federation_token": "string"      // Authentication token for federation
}
```

**Response**:

```json
{
  "status": "string",               // forwarded, rejected, error
  "forwarded_request_id": "string", // New request ID at target provider
  "message": "string",
  "error": {                        // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 202 Accepted: Request forwarded
- 400 Bad Request: Invalid request format
- 401 Unauthorized: Authentication failed
- 403 Forbidden: Federation not permitted
- 500 Internal Server Error: Server error

#### Add Federation Partner

Adds a new federation partner.

**HTTP Method**: POST  
**Path**: `/partners`  
**Content-Type**: application/json

**Request Body**:

```json
{
  "provider_id": "string",
  "name": "string",
  "url": "string",
  "contact_info": {
    "organization": "string",
    "email": "string",
    "phone": "string"
  },
  "trust_level": "string",           // trusted, limited, untrusted
  "federation_policies": {
    "auto_forward": "boolean",
    "capability_sharing": "boolean",
    "analytics_sharing": "boolean"
  },
  "shared_secret": "string"          // Secret for initial authentication
}
```

**Response**:

```json
{
  "status": "string",                // success, pending, error
  "partner_id": "string",
  "federation_token": "string",      // Token for future authentication
  "message": "string",
  "error": {                        // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 201 Created: Partner added successfully
- 202 Accepted: Partner addition pending
- 400 Bad Request: Invalid partner information
- 401 Unauthorized: Authentication failed
- 409 Conflict: Partner already exists
- 500 Internal Server Error: Server error

#### Remove Federation Partner

Removes a federation partner.

**HTTP Method**: DELETE  
**Path**: `/partners/{provider_id}`  
**Parameters**:
- `provider_id` (path): The ID of the partner to remove

**Response**:

```json
{
  "status": "string",                // success, error
  "message": "string",
  "error": {                        // Present only if status is "error"
    "code": "string",
    "message": "string"
  }
}
```

**Status Codes**:
- 200 OK: Partner removed successfully
- 404 Not Found: Partner not found
- 401 Unauthorized: Authentication failed
- 500 Internal Server Error: Server error

## Error Codes

| Code | Description |
|------|-------------|
| PROV_001 | Invalid request format |
| PROV_002 | Cell not found |
| PROV_003 | Capability not supported |
| PROV_004 | Invalid quantum signature |
| PROV_005 | Cell validation failed |
| PROV_006 | Request timed out |
| PROV_007 | Cell already exists |
| PROV_008 | Cell package corrupted |
| PROV_009 | Federation not enabled |
| PROV_010 | Federation partner not found |
| PROV_011 | Federation request rejected |
| PROV_012 | Analytics report invalid |
| PROV_013 | Rate limit exceeded |
| PROV_014 | Repository full |
| PROV_015 | Insufficient permissions |

## SDK Support

The Provider API is available in the following language SDKs:

- Python: `pip install qcc-provider-sdk`
- JavaScript: `npm install qcc-provider-sdk`
- Java: Maven dependency `ai.cellcomputing:qcc-provider-sdk:1.0.0`
- C#: NuGet package `QCC.Provider.SDK`
- Go: `go get github.com/cellcomputing/qcc-provider-sdk`

## Conclusion

This document specifies the Provider API for the QCC system. By implementing these interfaces, cell provider services can participate in the QCC ecosystem, providing cells to assemblers and collaborating with other providers through federation.

For examples and sample code, refer to the Provider API Tutorials document.

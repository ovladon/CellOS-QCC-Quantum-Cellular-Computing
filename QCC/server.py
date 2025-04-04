#!/usr/bin/env python3
"""
Server application for the QCC system.
Provides HTTP API endpoints for interacting with the QCC assembler.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import QCC components
from qcc.assembler.core.assembler import CellAssembler
from qcc.common.models import Solution
from qcc.assembler.security.auth import verify_token, get_user_id

logger = logging.getLogger("qcc.server")

# Initialize FastAPI app
app = FastAPI(
    title="QCC API",
    description="Quantum Cellular Computing API",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, limit this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store global components accessible to API routes
components: Dict[str, Any] = {}

# Define request and response models
class IntentRequest(BaseModel):
    user_request: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timeout_ms: Optional[int] = 30000
    priority: Optional[int] = 5

class IntentResponse(BaseModel):
    solution_id: str
    status: str
    estimated_completion_ms: int
    capabilities: list

# API routes
@app.get("/")
async def root():
    """Root endpoint for QCC API."""
    return {
        "name": "QCC API",
        "version": "0.1.0",
        "status": "active"
    }

@app.post("/api/v1/intent", response_model=IntentResponse)
async def create_intent(
    request: IntentRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id)
):
    """Submit a user intent to the QCC assembler."""
    assembler: CellAssembler = components["assembler"]
    
    try:
        # Create a solution
        solution = await assembler.assemble_solution(
            user_request=request.user_request,
            context=request.context
        )
        
        # Return response
        return {
            "solution_id": solution.id,
            "status": solution.status,
            "estimated_completion_ms": 5000,  # Example value
            "capabilities": [cell.capability for cell in solution.cells.values()]
        }
    except Exception as e:
        logger.error(f"Error creating solution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/solutions/{solution_id}")
async def get_solution(solution_id: str, user_id: str = Depends(get_user_id)):
    """Get details about a specific solution."""
    assembler: CellAssembler = components["assembler"]
    
    if solution_id not in assembler.active_solutions:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    solution = assembler.active_solutions[solution_id]
    return solution.to_dict()

@app.delete("/api/v1/solutions/{solution_id}")
async def release_solution(solution_id: str, user_id: str = Depends(get_user_id)):
    """Release a solution and its resources."""
    assembler: CellAssembler = components["assembler"]
    
    try:
        result = await assembler.release_solution(solution_id)
        if result:
            return {"status": "success", "message": "Solution released"}
        else:
            raise HTTPException(status_code=404, detail="Solution not found")
    except Exception as e:
        logger.error(f"Error releasing solution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/cells/{cell_id}/capabilities/{capability}")
async def execute_capability(
    cell_id: str,
    capability: str,
    parameters: Dict[str, Any],
    user_id: str = Depends(get_user_id)
):
    """Execute a specific capability on a cell."""
    assembler: CellAssembler = components["assembler"]
    
    # Find solution containing the cell
    solution_id = None
    for sid, solution in assembler.active_solutions.items():
        if cell_id in solution.cells:
            solution_id = sid
            break
    
    if not solution_id:
        raise HTTPException(status_code=404, detail="Cell not found in any active solution")
    
    try:
        # Execute capability
        result = await assembler.cell_runtime.execute_capability(
            cell_id=cell_id,
            capability=capability,
            parameters=parameters
        )
        return result
    except Exception as e:
        logger.error(f"Error executing capability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/status")
async def get_status():
    """Get the current status of the QCC system."""
    assembler: CellAssembler = components["assembler"]
    
    try:
        status = await assembler.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response

async def start_server(system_components: Dict[str, Any]):
    """Start the FastAPI server with the given components."""
    global components
    components = system_components
    
    config = components["config"]
    host = config["server"]["host"]
    port = config["server"]["port"]
    
    logger.info(f"Starting QCC API server on {host}:{port}")
    
    # Run the server
    config = uvicorn.Config(
        app="server:app",
        host=host,
        port=port,
        log_level="info",
        reload=config["server"].get("reload", False)
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    # This allows running the server directly, but components won't be initialized
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

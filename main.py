from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import asyncio
import os

from services.registry import ServiceRegistry
from services.linkedin_service import LinkedInService
from services.base import ServiceRequest
from routers import linkedin

load_dotenv()

app = FastAPI(
    title="MCP Server",
    description="A Model Context Protocol server for handling different services",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp = FastMCP("MCP Service Handler")
service_registry = ServiceRegistry()

# Initialize and register services
linkedin_service = LinkedInService()
service_registry.register_service(linkedin_service)

# Include routers
app.include_router(linkedin.router)

@app.get("/")
async def root():
    return {"message": "MCP Server is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "server_type": "mcp"}

@mcp.tool()
async def echo(message: str) -> str:
    """Echo a message back"""
    return f"Echo: {message}"

@mcp.tool()
async def linkedin_request(service_name: str, method: str, parameters: dict = None) -> dict:
    """Execute LinkedIn API requests through MCP"""
    if parameters is None:
        parameters = {}
    
    request = ServiceRequest(
        service_name=service_name,
        method=method,
        parameters=parameters
    )
    
    response = await service_registry.handle_request(request)
    return response.dict()

@app.get("/services")
async def list_services():
    """List all registered services"""
    return {
        "services": service_registry.list_services(),
        "methods": service_registry.get_all_methods()
    }

@app.post("/services/{service_name}/{method}")
async def call_service_method(service_name: str, method: str, parameters: dict = None):
    """Call a specific service method"""
    if parameters is None:
        parameters = {}
    
    request = ServiceRequest(
        service_name=service_name,
        method=method,
        parameters=parameters
    )
    
    response = await service_registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
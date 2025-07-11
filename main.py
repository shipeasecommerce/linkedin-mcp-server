import os
import requests
from typing import Dict, Any, Optional
from authlib.integrations.requests_client import OAuth2Session
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from contextlib import asynccontextmanager

from database import init_database, store_token, get_valid_token, delete_token, list_all_tokens
from services.registry import ServiceRegistry
from services.linkedin_service import LinkedInService
from services.base import ServiceRequest
from routers import linkedin

load_dotenv()

# Initialize service registry
service_registry = ServiceRegistry()
linkedin_service = LinkedInService()
service_registry.register_service(linkedin_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_database()
    yield
    # Shutdown
    pass

# Create FastAPI app
app = FastAPI(
    title="LinkedIn MCP Server",
    description="A Model Context Protocol server for LinkedIn API integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LinkedIn API configuration
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/linkedin/callback")
LINKEDIN_BASE_URL = "https://api.linkedin.com/v2"
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Create MCP server with dynamic base URL
def get_base_url():
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")
    return f"http://{host}:{port}"

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LinkedIn MCP Server is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server_type": "mcp"}

# LinkedIn OAuth endpoints
@app.get("/linkedin/auth")
async def linkedin_auth_redirect(
    scope: str = Query("openid profile email w_member_social"),
    state: str = Query("random_state")
):
    """Start LinkedIn OAuth flow by redirecting to authorization URL"""
    request = ServiceRequest(
        service_name="linkedin",
        method="start_auth_flow", 
        parameters={"scope": scope, "state": state}
    )
    
    response = await service_registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    
    # Redirect to LinkedIn authorization URL
    return RedirectResponse(url=response.data["redirect_url"])

@app.get("/linkedin/callback")
async def linkedin_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None), 
    error_description: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    user_id: str = Query("default_user")
):
    """Handle LinkedIn OAuth callback"""
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"LinkedIn OAuth error: {error} - {error_description}"
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")
    
    # Exchange code for token using service registry
    request = ServiceRequest(
        service_name="linkedin",
        method="exchange_code_for_token",
        parameters={"code": code, "user_id": user_id}
    )
    
    response = await service_registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {response.error}")
    
    # Return an HTML response for better user experience
    success_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LinkedIn Authentication Complete</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .success {{ color: green; font-size: 24px; margin-bottom: 20px; }}
            .details {{ background: #f5f5f5; padding: 20px; border-radius: 5px; max-width: 600px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="success">✅ LinkedIn Authentication Successful!</div>
        <div class="details">
            <p><strong>User ID:</strong> {response.data.get('user_id', 'default_user')}</p>
            <p><strong>Token Type:</strong> {response.data.get('token_type', 'Bearer')}</p>
            <p><strong>Expires:</strong> {response.data.get('expires_at', 'Not specified')}</p>
            <p><strong>Scope:</strong> {response.data.get('scope', 'Not specified')}</p>
            <hr>
            <p>You can now close this window. Your LinkedIn token has been securely stored and you can use LinkedIn API endpoints.</p>
        </div>
        <script>
            // Auto-close after 5 seconds
            setTimeout(() => {{
                window.close();
            }}, 5000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=success_html)

@app.get("/mcp-info")
async def mcp_info():
    """Get MCP server information"""
    # Get host and port from environment or defaults
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")
    base_url = f"http://{host}:{port}"
    
    return {
        "mcp_server": "LinkedIn MCP Server",
        "description": "FastAPI-MCP integration for LinkedIn API",
        "host": host,
        "port": port,
        "base_url": base_url,
        "mcp_endpoint": f"{base_url}/mcp",
        "available_tools": [
            "start_linkedin_auth",
            "linkedin_callback", 
            "get_auth_url",
            "exchange_token",
            "get_profile",
            "get_user_info", 
            "get_connections",
            "get_posts",
            "create_post"
        ],
        "documentation": f"{base_url}/docs"
    }


# Include LinkedIn router
app.include_router(linkedin.router)

# MCP endpoint for Model Context Protocol integration
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP endpoint for Model Context Protocol integration"""
    body = None
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        
        # Handle MCP requests through the service registry
        if method == "tools/list":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "start_linkedin_auth",
                            "description": "Start LinkedIn OAuth authentication flow",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "scope": {"type": "string", "default": "openid profile email w_member_social w_organization_social r_organization_social r_compliance r_member_social r_dma_admin_pages_content"}
                                }
                            }
                        },
                        {
                            "name": "get_profile",
                            "description": "Get LinkedIn user profile",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string", "default": "default_user"},
                                    "access_token": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "get_posts",
                            "description": "Get LinkedIn user's posts",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string", "default": "default_user"},
                                    "access_token": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "create_post",
                            "description": "Create a LinkedIn post",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "user_id": {"type": "string", "default": "default_user"}
                                },
                                "required": ["content"]
                            }
                        },
                        {
                            "name": "get_experience",
                            "description": "Get LinkedIn user's job experience",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string", "default": "default_user"},
                                    "access_token": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "get_courses",
                            "description": "Get LinkedIn user's courses",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string", "default": "default_user"},
                                    "access_token": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "get_certifications",
                            "description": "Get LinkedIn user's certifications",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string", "default": "default_user"},
                                    "access_token": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "search_jobs",
                            "description": "Search for LinkedIn jobs",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string", "default": "python"},
                                    "count": {"type": "integer", "default": 2},
                                    "location": {"type": "string"},
                                    "company": {"type": "string"},
                                    "user_id": {"type": "string", "default": "default_user"},
                                    "access_token": {"type": "string"}
                                }
                            }
                        }
                    ]
                }
            })
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})
            
            # Map tool calls to service requests
            if tool_name == "start_linkedin_auth":
                from services.base import ServiceRequest
                service_request = ServiceRequest(
                    service_name="linkedin",
                    method="get_auth_url",
                    parameters=tool_params
                )
                auth_url_response = await service_registry.handle_request(service_request)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Please visit this URL to authenticate: {auth_url_response.data.get('auth_url')}"
                            }
                        ]
                    }
                })
            
            elif tool_name in ["get_profile", "create_post", "get_posts", "get_experience", "get_courses", "get_certifications", "search_jobs"]:
                from services.base import ServiceRequest
                service_request = ServiceRequest(
                    service_name="linkedin",
                    method=tool_name,
                    parameters=tool_params
                )
                response = await service_registry.handle_request(service_request)
                
                return JSONResponse({
                    "jsonrpc": "2.0", 
                    "id": body.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(response.data) if response.success else f"Error: {response.error}"
                            }
                        ]
                    }
                })
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32601, "message": "Method not found"}
        })
        
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id") if body else None,
            "error": {"code": -32000, "message": str(e)}
        })

# OAuth well-known endpoints for MCP integration
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """OAuth 2.0 Authorization Server Metadata - Compatible with MCP"""
    base_url = get_base_url()
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/linkedin/auth", 
        "token_endpoint": f"{base_url}/linkedin/exchange-token",
        "registration_endpoint": f"{base_url}/.well-known/oauth-client-registration",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "scopes_supported": ["openid", "profile", "w_member_social"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
        "client_registration_types_supported": ["dynamic"],
        "code_challenge_methods_supported": ["S256", "plain"]
    }

@app.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_mcp():
    """OAuth 2.0 Authorization Server Metadata for MCP path"""
    return await oauth_authorization_server()

@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth 2.0 Protected Resource Metadata"""
    base_url = get_base_url()
    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "scopes_supported": ["openid", "profile", "w_member_social"],
        "bearer_methods_supported": ["header"]
    }

@app.post("/.well-known/oauth-client-registration")
async def oauth_client_registration(request_data: dict):
    """Dynamic Client Registration endpoint"""
    # For MCP compatibility, accept any client registration
    client_id = f"mcp_client_{hash(str(request_data)) % 10000}"
    base_url = get_base_url()
    
    return {
        "client_id": client_id,
        "client_secret": "mcp_secret",
        "redirect_uris": request_data.get("redirect_uris", [f"{base_url}/linkedin/callback"]),
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none"
    }

@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon response"""
    return {"message": "No favicon configured"}

# MCP endpoint is automatically handled by the mount() call above

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "localhost")
    uvicorn.run(app, host=host, port=port)
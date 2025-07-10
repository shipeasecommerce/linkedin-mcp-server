import os
import requests
from typing import Dict, Any, Optional
from authlib.integrations.requests_client import OAuth2Session
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="LinkedIn MCP Server",
    description="A Model Context Protocol server for LinkedIn API integration",
    version="1.0.0"
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

# Create MCP server
mcp = FastApiMCP(
    app,
    name="LinkedIn MCP Server",
    description="LinkedIn API integration via MCP"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LinkedIn MCP Server is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server_type": "mcp"}

@app.post("/linkedin/auth-url")
async def get_linkedin_auth_url(
    scope: str = "r_liteprofile r_emailaddress w_member_social", 
    state: str = "random_state"
) -> Dict[str, str]:
    """Generate LinkedIn OAuth authorization URL"""
    client = OAuth2Session(
        LINKEDIN_CLIENT_ID, 
        redirect_uri=LINKEDIN_REDIRECT_URI,
        scope=scope
    )
    
    authorization_url, state = client.create_authorization_url(
        LINKEDIN_AUTH_URL,
        state=state
    )
    
    return {
        "auth_url": authorization_url,
        "state": state
    }

@app.post("/linkedin/exchange-token")
async def exchange_linkedin_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token"""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")
    
    client = OAuth2Session(LINKEDIN_CLIENT_ID, redirect_uri=LINKEDIN_REDIRECT_URI)
    token = client.fetch_token(
        LINKEDIN_TOKEN_URL,
        code=code,
        client_secret=LINKEDIN_CLIENT_SECRET
    )
    
    return {"token": token}

async def make_authenticated_linkedin_request(token: str, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
    """Make authenticated request to LinkedIn API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{LINKEDIN_BASE_URL}/{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    response.raise_for_status()
    return response.json()

@app.get("/linkedin/profile")
async def get_linkedin_profile(access_token: str) -> Dict[str, Any]:
    """Get user's LinkedIn profile"""
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    profile_data = await make_authenticated_linkedin_request(
        access_token, 
        "people/~:(id,first-name,last-name,headline,public-profile-url,picture-url)"
    )
    
    return profile_data

@app.get("/linkedin/user-info")
async def get_linkedin_user_info(access_token: str) -> Dict[str, Any]:
    """Get user's basic info and email"""
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    # Get profile info
    profile = await make_authenticated_linkedin_request(
        access_token,
        "people/~:(id,first-name,last-name,headline)"
    )
    
    # Get email address
    email_data = await make_authenticated_linkedin_request(
        access_token,
        "emailAddress?q=members&projection=(elements*(handle~))"
    )
    
    return {
        "profile": profile,
        "email": email_data
    }

@app.get("/linkedin/connections")
async def get_linkedin_connections(access_token: str) -> Dict[str, Any]:
    """Get user's connections"""
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    connections = await make_authenticated_linkedin_request(
        access_token,
        "connections"
    )
    
    return connections

@app.get("/linkedin/posts")
async def get_linkedin_posts(access_token: str) -> Dict[str, Any]:
    """Get user's posts/shares"""
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    posts = await make_authenticated_linkedin_request(
        access_token,
        "shares?q=owners&owners=urn:li:person:{person-id}"
    )
    
    return posts

@app.post("/linkedin/posts")
async def create_linkedin_post(access_token: str, content: str) -> Dict[str, Any]:
    """Create a new LinkedIn post"""
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    if not content:
        raise HTTPException(status_code=400, detail="Post content is required")
    
    post_data = {
        "content": {
            "contentEntities": [],
            "title": content
        },
        "distribution": {
            "linkedInDistributionTarget": {}
        },
        "owner": "urn:li:person:{person-id}",
        "subject": content[:100]  # Truncate for subject
    }
    
    result = await make_authenticated_linkedin_request(
        access_token,
        "shares",
        method="POST",
        data=post_data
    )
    
    return result

# Mount the MCP server
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
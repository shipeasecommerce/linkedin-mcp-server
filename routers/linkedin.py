from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from services.registry import ServiceRegistry
from services.base import ServiceRequest

router = APIRouter(prefix="/linkedin", tags=["LinkedIn"])

class AuthRequest(BaseModel):
    scope: Optional[str] = "openid profile email w_member_social"
    state: Optional[str] = "random_state"

class TokenRequest(BaseModel):
    code: str
    user_id: str = "default_user"

class PostRequest(BaseModel):
    content: str
    access_token: Optional[str] = None
    user_id: str = "default_user"

def get_service_registry() -> ServiceRegistry:
    from main import service_registry
    return service_registry

@router.get("/auth")
async def start_linkedin_auth(
    scope: str = Query("openid profile email w_member_social"),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Start LinkedIn OAuth flow by redirecting to authorization URL"""
    request = ServiceRequest(
        service_name="linkedin",
        method="start_auth_flow",
        parameters={"scope": scope}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)
    
    # Return redirect response to authorization URL
    return RedirectResponse(url=response.data["redirect_url"])

@router.get("/callback")
async def linkedin_callback(
    code: Optional[str] = None, 
    error: Optional[str] = None, 
    error_description: Optional[str] = None, 
    state: Optional[str] = None,
    user_id: str = Query("default_user"),
    registry: ServiceRegistry = Depends(get_service_registry)
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
    
    response = await registry.handle_request(request)
    
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
            // Try to close the window, or show instruction
            setTimeout(() => {{
                if (window.opener) {{
                    window.close();
                }} else {{
                    // If can't close, show message to manually close
                    document.body.innerHTML += '<p style="color: blue; margin-top: 20px;">You can now close this tab manually.</p>';
                }}
            }}, 2000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=success_html)

@router.post("/auth-url")
async def get_auth_url(
    auth_request: AuthRequest,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get LinkedIn OAuth authorization URL"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_auth_url",
        parameters={"scope": auth_request.scope, "state": auth_request.state}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.post("/exchange-token")
async def exchange_token(
    token_request: TokenRequest,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Exchange authorization code for access token"""
    request = ServiceRequest(
        service_name="linkedin",
        method="exchange_code_for_token",
        parameters={"code": token_request.code, "user_id": token_request.user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.get("/profile")
async def get_profile(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's LinkedIn profile"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_profile",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.get("/user-info")
async def get_user_info(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's basic info and email"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_user_info",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.get("/connections")
async def get_connections(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's connections"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_connections",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.get("/posts")
async def get_posts(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's posts/shares"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_posts",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.post("/posts")
async def create_post(
    post_request: PostRequest,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Create a new LinkedIn post"""
    request = ServiceRequest(
        service_name="linkedin",
        method="create_post",
        parameters={
            "access_token": post_request.access_token,
            "content": post_request.content,
            "user_id": post_request.user_id
        }
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.get("/certifications")
async def get_certifications(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's LinkedIn certifications"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_certifications",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.get("/courses")
async def get_courses(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's LinkedIn courses"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_courses",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.get("/experience")
async def get_experience(
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's LinkedIn job experience"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_experience",
        parameters={"access_token": access_token, "user_id": user_id}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=401, detail=response.error)
    
    return response.data

@router.get("/search-jobs")
async def search_jobs(
    title: str = Query("python"),
    count: int = Query(2),
    location: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    user_id: str = Query("default_user"),
    access_token: Optional[str] = Query(None),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Search for LinkedIn jobs"""
    request = ServiceRequest(
        service_name="linkedin",
        method="search_jobs",
        parameters={
            "title": title,
            "count": count,
            "location": location,
            "company": company,
            "access_token": access_token,
            "user_id": user_id
        }
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data
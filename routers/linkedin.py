from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.registry import ServiceRegistry
from services.base import ServiceRequest

router = APIRouter(prefix="/linkedin", tags=["LinkedIn"])

class AuthRequest(BaseModel):
    scope: Optional[str] = "r_liteprofile r_emailaddress w_member_social"
    state: Optional[str] = "random_state"

class TokenRequest(BaseModel):
    code: str

class PostRequest(BaseModel):
    content: str
    access_token: str

def get_service_registry() -> ServiceRegistry:
    from main import service_registry
    return service_registry

@router.get("/auth")
async def get_auth_url(
    scope: str = Query("r_liteprofile r_emailaddress w_member_social"),
    state: str = Query("random_state"),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get LinkedIn OAuth authorization URL"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_auth_url",
        parameters={"scope": scope, "state": state}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.post("/token")
async def exchange_token(
    token_request: TokenRequest,
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Exchange authorization code for access token"""
    request = ServiceRequest(
        service_name="linkedin",
        method="exchange_code_for_token",
        parameters={"code": token_request.code}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.get("/profile")
async def get_profile(
    access_token: str = Query(...),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's LinkedIn profile"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_profile",
        parameters={"access_token": access_token}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.get("/user-info")
async def get_user_info(
    access_token: str = Query(...),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's basic info and email"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_user_info",
        parameters={"access_token": access_token}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.get("/connections")
async def get_connections(
    access_token: str = Query(...),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's connections"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_connections",
        parameters={"access_token": access_token}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data

@router.get("/posts")
async def get_posts(
    access_token: str = Query(...),
    registry: ServiceRegistry = Depends(get_service_registry)
):
    """Get user's posts/shares"""
    request = ServiceRequest(
        service_name="linkedin",
        method="get_posts",
        parameters={"access_token": access_token}
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
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
            "content": post_request.content
        }
    )
    
    response = await registry.handle_request(request)
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.error)
    
    return response.data
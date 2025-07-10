import os
import requests
from typing import Dict, Any, List, Optional
from authlib.integrations.requests_client import OAuth2Session
from .base import BaseService, ServiceRequest, ServiceResponse

class LinkedInService(BaseService):
    """LinkedIn API service for MCP server"""
    
    def __init__(self):
        super().__init__("linkedin")
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/linkedin/callback")
        self.base_url = "https://api.linkedin.com/v2"
        self.auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        
    def get_available_methods(self) -> List[str]:
        return [
            "get_auth_url",
            "exchange_code_for_token", 
            "get_profile",
            "get_user_info",
            "get_connections",
            "get_posts",
            "create_post"
        ]
    
    async def handle_request(self, request: ServiceRequest) -> ServiceResponse:
        """Handle LinkedIn service requests"""
        method = request.method
        params = request.parameters
        
        try:
            if method == "get_auth_url":
                return await self._get_auth_url(params)
            elif method == "exchange_code_for_token":
                return await self._exchange_code_for_token(params)
            elif method == "get_profile":
                return await self._get_profile(params)
            elif method == "get_user_info":
                return await self._get_user_info(params)
            elif method == "get_connections":
                return await self._get_connections(params)
            elif method == "get_posts":
                return await self._get_posts(params)
            elif method == "create_post":
                return await self._create_post(params)
            else:
                return ServiceResponse(
                    success=False,
                    error=f"Unknown method: {method}"
                )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"LinkedIn API error: {str(e)}"
            )
    
    async def _get_auth_url(self, params: Dict[str, Any]) -> ServiceResponse:
        """Generate LinkedIn OAuth authorization URL"""
        scope = params.get("scope", "r_liteprofile r_emailaddress w_member_social")
        state = params.get("state", "random_state")
        
        client = OAuth2Session(
            self.client_id, 
            redirect_uri=self.redirect_uri,
            scope=scope
        )
        
        authorization_url, state = client.create_authorization_url(
            self.auth_url,
            state=state
        )
        
        return ServiceResponse(
            success=True,
            data={
                "auth_url": authorization_url,
                "state": state
            }
        )
    
    async def _exchange_code_for_token(self, params: Dict[str, Any]) -> ServiceResponse:
        """Exchange authorization code for access token"""
        code = params.get("code")
        if not code:
            return ServiceResponse(
                success=False,
                error="Authorization code is required"
            )
        
        client = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri)
        token = client.fetch_token(
            self.token_url,
            code=code,
            client_secret=self.client_secret
        )
        
        return ServiceResponse(
            success=True,
            data={"token": token}
        )
    
    async def _make_authenticated_request(self, token: str, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make authenticated request to LinkedIn API"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    async def _get_profile(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's LinkedIn profile"""
        token = params.get("access_token")
        if not token:
            return ServiceResponse(
                success=False,
                error="Access token is required"
            )
        
        profile_data = await self._make_authenticated_request(
            token, 
            "people/~:(id,first-name,last-name,headline,public-profile-url,picture-url)"
        )
        
        return ServiceResponse(
            success=True,
            data=profile_data
        )
    
    async def _get_user_info(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's basic info and email"""
        token = params.get("access_token")
        if not token:
            return ServiceResponse(
                success=False,
                error="Access token is required"
            )
        
        # Get profile info
        profile = await self._make_authenticated_request(
            token,
            "people/~:(id,first-name,last-name,headline)"
        )
        
        # Get email address
        email_data = await self._make_authenticated_request(
            token,
            "emailAddress?q=members&projection=(elements*(handle~))"
        )
        
        return ServiceResponse(
            success=True,
            data={
                "profile": profile,
                "email": email_data
            }
        )
    
    async def _get_connections(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's connections"""
        token = params.get("access_token")
        if not token:
            return ServiceResponse(
                success=False,
                error="Access token is required"
            )
        
        connections = await self._make_authenticated_request(
            token,
            "connections"
        )
        
        return ServiceResponse(
            success=True,
            data=connections
        )
    
    async def _get_posts(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's posts/shares"""
        token = params.get("access_token")
        if not token:
            return ServiceResponse(
                success=False,
                error="Access token is required"
            )
        
        posts = await self._make_authenticated_request(
            token,
            "shares?q=owners&owners=urn:li:person:{person-id}"
        )
        
        return ServiceResponse(
            success=True,
            data=posts
        )
    
    async def _create_post(self, params: Dict[str, Any]) -> ServiceResponse:
        """Create a new LinkedIn post"""
        token = params.get("access_token")
        content = params.get("content")
        
        if not token:
            return ServiceResponse(
                success=False,
                error="Access token is required"
            )
        
        if not content:
            return ServiceResponse(
                success=False,
                error="Post content is required"
            )
        
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
        
        result = await self._make_authenticated_request(
            token,
            "shares",
            method="POST",
            data=post_data
        )
        
        return ServiceResponse(
            success=True,
            data=result
        )
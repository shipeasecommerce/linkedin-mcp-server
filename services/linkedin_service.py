import os
import requests
from typing import Dict, Any, List
from authlib.integrations.requests_client import OAuth2Session
from .base import BaseService, ServiceRequest, ServiceResponse
from database import store_token, get_valid_token

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
            "create_post",
            "start_auth_flow",
            "get_certifications",
            "get_courses",
            "get_experience"
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
            elif method == "start_auth_flow":
                return await self._start_auth_flow(params)
            elif method == "get_certifications":
                return await self._get_certifications(params)
            elif method == "get_courses":
                return await self._get_courses(params)
            elif method == "get_experience":
                return await self._get_experience(params)
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
    
    async def _start_auth_flow(self, params: Dict[str, Any]) -> ServiceResponse:
        """Start LinkedIn OAuth flow - returns redirect URL without blocking"""
        scope = params.get("scope", "openid profile email w_member_social w_organization_social r_organization_social r_compliance r_member_social r_ads rw_ads r_marketing_solutions rw_marketing_solutions")
        state = params.get("state", "secure_random_state")
        
        if not self.client_id or not self.client_secret:
            return ServiceResponse(
                success=False,
                error="LinkedIn OAuth credentials not configured. Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET environment variables."
            )
        
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
                "redirect_url": authorization_url,
                "state": state,
                "message": "Visit the redirect_url to authorize the application. After authorization, you'll be redirected to the callback URL where the token will be automatically stored."
            }
        )

    async def _get_auth_url(self, params: Dict[str, Any]) -> ServiceResponse:
        """Generate LinkedIn OAuth authorization URL"""
        scope = params.get("scope", "openid profile email w_member_social w_organization_social r_organization_social r_compliance r_member_social r_ads rw_ads r_marketing_solutions rw_marketing_solutions")
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
        """Exchange authorization code for access token and store in database"""
        code = params.get("code")
        user_id = params.get("user_id", "default_user")
        
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
        
        # Fetch user email using OpenID Connect userinfo endpoint
        user_email = None
        try:
            userinfo_data = await self._make_authenticated_request(
                token['access_token'],
                "../userinfo"  # This goes to https://api.linkedin.com/v2/userinfo
            )
            user_email = userinfo_data.get('email')
            print(f"User email: {user_email}")
        except Exception as e:
            # If email fetch fails, continue without email
            print(f"Failed to fetch email: {e}")
            pass
        
        # Store token in database with email
        stored_token = await store_token(user_id, token, user_email)
        
        return ServiceResponse(
            success=True,
            data={
                "message": "Token stored successfully in database",
                "user_id": stored_token.user_id,
                "email": stored_token.email,
                "token_type": stored_token.token_type,
                "expires_at": stored_token.expires_at.isoformat() if stored_token.expires_at else None,
                "scope": stored_token.scope
            }
        )
    
    async def _make_authenticated_request(self, token: str, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make authenticated request to LinkedIn API"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Add LinkedIn API version headers for Posts API
        if endpoint in ["posts", "rest/posts", "ugcPosts"]:
            headers.update({
                "LinkedIn-Version": "202411",
                "X-Restli-Protocol-Version": "2.0.0"
            })
        
        # Handle special endpoints
        if endpoint.startswith("../"):
            # For userinfo endpoint: ../userinfo -> https://api.linkedin.com/v2/userinfo
            url = f"https://api.linkedin.com/v2/{endpoint[3:]}"
        elif endpoint.startswith("rest/"):
            # For REST API endpoints: rest/posts -> https://api.linkedin.com/rest/posts
            url = f"https://api.linkedin.com/{endpoint}"
        else:
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
        """Get user's LinkedIn profile using stored or provided token"""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")
        
        # Use stored token if no token provided
        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token
        
        profile_data = await self._make_authenticated_request(
            access_token, 
            "../userinfo"
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
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")

        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token
        
        # Get user profile to get person URN
        try:
            profile_data = await self._make_authenticated_request(
                access_token, 
                "../userinfo"
            )
            person_id = profile_data.get('sub')  # This is the person ID from userinfo
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Failed to get user profile for fetching posts: {str(e)}"
            )

        posts = await self._make_authenticated_request(
            access_token,
            f"rest/posts?author=urn:li:person:{person_id}&q=author"
        )
        
        return ServiceResponse(
            success=True,
            data=posts
        )
    
    async def _create_post(self, params: Dict[str, Any]) -> ServiceResponse:
        """Create a new LinkedIn post"""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")
        content = params.get("content")
        
        # Use stored token if no token provided
        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token
        
        if not content:
            return ServiceResponse(
                success=False,
                error="Post content is required"
            )
        
        # Get user profile to get person URN
        try:
            profile_data = await self._make_authenticated_request(
                access_token, 
                "../userinfo"
            )
            person_id = profile_data.get('sub')  # This is the person ID from userinfo
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Failed to get user profile for posting: {str(e)}"
            )
        
        # Use UGC Posts API format
        post_data = {
            "author": f"urn:li:person:{person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        result = await self._make_authenticated_request(
            access_token,
            "ugcPosts",
            method="POST",
            data=post_data
        )
        
        return ServiceResponse(
            success=True,
            data=result
        )

    async def _get_certifications(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's LinkedIn certifications"""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")

        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token

        try:
            certifications_data = await self._make_authenticated_request(
                access_token,
                "me?projection=(certifications*(id,name,authority,startDate,endDate))"
            )
            return ServiceResponse(
                success=True,
                data=certifications_data.get('certifications', {})
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return ServiceResponse(
                    success=False,
                    error="Permission denied. Your access token may not have the necessary 'r_compliance' or 'r_basicprofile' permissions for certifications."
                )
            return ServiceResponse(
                success=False,
                error=f"Failed to fetch certifications: {e}. Check LinkedIn API documentation for correct endpoint and permissions."
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"An unexpected error occurred while fetching certifications: {e}"
            )

    async def _get_courses(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's LinkedIn courses"""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")

        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token

        try:
            courses_data = await self._make_authenticated_request(
                access_token,
                "me?projection=(courses*(id,name,authority))"
            )
            return ServiceResponse(
                success=True,
                data=courses_data.get('courses', {})
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return ServiceResponse(
                    success=False,
                    error="Permission denied. Your access token may not have the necessary 'r_compliance' or 'r_basicprofile' permissions for courses."
                )
            return ServiceResponse(
                success=False,
                error=f"Failed to fetch courses: {e}. Check LinkedIn API documentation for correct endpoint and permissions."
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"An unexpected error occurred while fetching courses: {e}"
            )

    async def _get_experience(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's LinkedIn job experience"""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")

        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token

        try:
            experience_data = await self._make_authenticated_request(
                access_token,
                "me?projection=(positions*(id,title,companyName,startDate,endDate,location))"
            )
            return ServiceResponse(
                success=True,
                data=experience_data.get('positions', {})
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return ServiceResponse(
                    success=False,
                    error="Permission denied. Your access token may not have the necessary permissions for job experience."
                )
            return ServiceResponse(
                success=False,
                error=f"Failed to fetch job experience: {e}. Check LinkedIn API documentation for correct endpoint and permissions."
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"An unexpected error occurred while fetching job experience: {e}"
            )
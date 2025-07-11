import os
import requests
from typing import Dict, Any, List
from authlib.integrations.requests_client import OAuth2Session
from linkedin import linkedin # This is the python3-linkedin library
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

    def _get_linkedin_client(self, access_token: str) -> linkedin.LinkedInApplication:
        """Create LinkedIn API client using python3-linkedin library"""
        # The python3-linkedin library's authentication object expects a 'token' attribute
        # which is usually populated after the OAuth flow. We'll create a dummy object
        # for existing access tokens.

        # It's important to pass the correct permissions list if the client needs to initiate auth,
        # but for just using an existing token, the actual list might not matter as much
        # as long as the token itself has the permissions.
        authentication = linkedin.LinkedInAuthentication(
            self.client_id,
            self.client_secret,
            self.redirect_uri,
            # This is a critical point: PERMISSIONS.enums.values() gives all known permissions.
            # Ensure the token obtained by the user actually has these scopes.
            # If you only want to use the token, you might not strictly need all these in the client init,
            # but it's good practice if the client object is also used for auth initiation.
            linkedin.PERMISSIONS.enums.values()
        )

        # Create a simple token object with access_token attribute
        class SimpleToken:
            def __init__(self, access_token):
                self.access_token = access_token
                self.token_type = 'Bearer' # Standard for OAuth2 access tokens

        authentication.token = SimpleToken(access_token)

        return linkedin.LinkedInApplication(authentication)

    def get_available_methods(self) -> List[str]:
        return [
            "get_auth_url",
            "exchange_code_for_token",
            "get_profile",
            "get_user_info", # Note: SDK doesn't have a direct 'user_info' equivalent, will rely on profile
            "get_connections",
            "get_posts",
            "create_post",
            "start_auth_flow",
            "get_certifications",
            "get_courses",
            "get_experience",
            "search_jobs"
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
            elif method == "search_jobs":
                return await self._search_jobs(params)
            else:
                return ServiceResponse(
                    success=False,
                    error=f"Unknown method: {method}"
                )
        except Exception as e:
            # Catch all exceptions and return a consistent error response
            return ServiceResponse(
                success=False,
                error=f"LinkedIn API error: {str(e)}"
            )

    async def _start_auth_flow(self, params: Dict[str, Any]) -> ServiceResponse:
        """Start LinkedIn OAuth flow - returns redirect URL without blocking"""
        # The python3-linkedin SDK can generate the auth URL
        scope = params.get("scope", "openid profile email w_member_social")
        state = params.get("state", "secure_random_state") # Remember to generate a unique state in production!

        if not self.client_id or not self.client_secret:
            return ServiceResponse(
                success=False,
                error="LinkedIn OAuth credentials not configured. Please set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET environment variables."
            )

        # We'll use authlib's OAuth2Session for the initial URL generation as it's more robust for this
        # and doesn't require the LinkedInApplication client (which expects an existing token or full auth setup).
        client = OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri,
            scope=scope
        )

        authorization_url, state = client.create_authorization_url(
            self.auth_url,
            state=state # Use the passed or default state
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
        # This method is very similar to _start_auth_flow; we can keep them separate
        # if they serve slightly different frontend/backend initiation patterns.
        scope = params.get("scope", "openid profile email w_member_social")
        state = params.get("state", "random_state") # Again, generate a secure random state for production

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

        # Use authlib's OAuth2Session to fetch the token, as python3-linkedin is primarily for API calls post-auth
        client = OAuth2Session(self.client_id, redirect_uri=self.redirect_uri)
        token = client.fetch_token(
            self.token_url,
            code=code,
            client_secret=self.client_secret
        )

        # Fetch user email using OpenID Connect userinfo endpoint
        # The python3-linkedin SDK does not have a direct userinfo method, so keep the direct request.
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
        """
        Make authenticated request to LinkedIn API using requests,
        primarily for endpoints not directly supported by python3-linkedin SDK.
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Add LinkedIn API version headers for Posts API
        # LinkedIn is moving to a new versioning model. "posts" and "ugcPosts" might need specific versions.
        # Check LinkedIn's latest API documentation for the correct headers.
        if endpoint in ["ugcPosts", "rest/posts"]: # Assuming 'posts' directly maps to ugcPosts or similar
            headers.update({
                "LinkedIn-Version": "202411", # Example: Adjust to current stable version
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

        # Use aiohttp or httpx for true async requests if this service is truly async from FastAPI.
        # For simplicity, keeping requests here, but noting it's blocking.
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status() # Raise an exception for bad status codes
        return response.json()

    async def _get_profile(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's LinkedIn profile using stored or provided token."""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")
        selectors = params.get("selectors", None)

        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token

        try:
            # Default selectors if none are provided
            default_selectors = [
                'id', 'firstName', 'lastName', 'profilePicture(displayImage~:elements*(identifiers*))',
                'vanityName', 'headline', 'summary', 'positions', 'educations',
                'certifications', 'courses', 'skills', 'emailAddress'
            ]

            projection_string = ""
            if selectors:
                # Convert list of selectors to LinkedIn API projection format
                # Example: ['id', 'first-name'] -> '(id,firstName)'
                # Note: LinkedIn API uses camelCase for fields, so convert if necessary
                camel_case_selectors = []
                for s in selectors:
                    if '-' in s:
                        parts = s.split('-')
                        camel_case_selectors.append(parts[0] + ''.join(p.capitalize() for p in parts[1:]))
                    else:
                        camel_case_selectors.append(s)
                projection_string = f"({','.join(camel_case_selectors)})"
            else:
                # Use a comprehensive default projection
                projection_string = f"({','.join(default_selectors)})"

            profile_data = await self._make_authenticated_request(
                access_token,
                f"me?projection={projection_string}"
            )

            return ServiceResponse(
                success=True,
                data=profile_data
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Profile fetch failed: {str(e)}"
            )

    async def _get_user_info(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's basic info and email."""
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
            # Use the /v2/me endpoint with projection for both profile and email
            user_info_data = await self._make_authenticated_request(
                access_token,
                "me?projection=(id,firstName,lastName,emailAddress)"
            )
            
            profile_data = {
                "id": user_info_data.get('id'),
                "firstName": user_info_data.get('firstName'),
                "lastName": user_info_data.get('lastName')
            }
            user_email = user_info_data.get('emailAddress', {}).get('elements', [{}])[0].get('handle~', {}).get('emailAddress')

            return ServiceResponse(
                success=True,
                data={
                    "profile": profile_data,
                    "email": user_email
                }
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Failed to fetch user info: {str(e)}"
            )

    async def _get_connections(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's connections. The python3-linkedin SDK's `get_connections`
        method might be limited to V1 API or specific scopes.
        Direct V2 API call is generally more reliable for recent APIs."""
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
            linkedin_client = self._get_linkedin_client(access_token)
            # The SDK's get_connections() might return an older API response format or require
            # specific V1 permissions if LinkedIn has deprecated it for V2.
            # For V2, the endpoint is typically `me/connections` or requires specific partnership access.
            # It's highly probable the SDK's `get_connections` is deprecated or requires old scopes.
            # Keeping the SDK call for demonstration but noting its potential limitations.
            connections_data = linkedin_client.get_connections()
            return ServiceResponse(
                success=True,
                data=connections_data
            )
        except Exception as e:
            # Fallback to direct request if SDK fails or for more granular control.
            # Note: Access to connections (V2) is often restricted to specific partner programs.
            try:
                # This V2 endpoint is often restricted.
                connections_data = await self._make_authenticated_request(
                    access_token,
                    "connections?q=viewer" # This endpoint typically requires specific partnership access
                )
                return ServiceResponse(
                    success=True,
                    data=connections_data
                )
            except Exception as fallback_error:
                return ServiceResponse(
                    success=False,
                    error=f"Connections fetch failed via SDK and direct request: {str(e)} (fallback error: {str(fallback_error)}). Note: Connections API access is often restricted by LinkedIn."
                )

    async def _get_posts(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's posts/shares, preferring the SDK's `get_network_updates`."""
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
            linkedin_client = self._get_linkedin_client(access_token)
            # get_network_updates() often fetches updates that appear in the user's feed,
            # which may include their own posts.
            posts_data = linkedin_client.get_network_updates()
            return ServiceResponse(
                success=True,
                data=posts_data
            )
        except Exception as e:
            # Fallback to direct V2 API request if SDK fails, focusing on UGC Posts API.
            try:
                # Need the authenticated user's URN for fetching their own UGC posts.
                profile_data = await self._make_authenticated_request(
                    access_token,
                    "../userinfo"
                )
                person_urn = f"urn:li:person:{profile_data.get('sub')}"

                # Fetch UGC posts by author.
                # Adjust the `q` parameter and projection as needed.
                # Example: `q=author&author={person_urn}`
                posts = await self._make_authenticated_request(
                    access_token,
                    f"ugcPosts?q=authors&authors={person_urn}&shares=true", # 'shares=true' to filter for shares
                    method="GET"
                )

                return ServiceResponse(
                    success=True,
                    data=posts
                )
            except Exception as fallback_error:
                return ServiceResponse(
                    success=False,
                    error=f"Posts fetch failed via SDK and direct request: {str(e)} (fallback error: {str(fallback_error)})"
                )

    async def _create_post(self, params: Dict[str, Any]) -> ServiceResponse:
        """Create a new LinkedIn post. The python3-linkedin SDK's `submit_share`
        or `submit_network_update` might be for older APIs or simpler shares.
        The V2 UGC Posts API is generally more robust and flexible."""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")
        content = params.get("content")

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

        try:
            linkedin_client = self._get_linkedin_client(access_token)
            # The SDK's `submit_share` or `submit_network_update` can be used.
            # However, the V2 UGC Posts API offers more control (e.g., specific share content types).
            # For this example, we'll try the SDK first.

            # Note: `submit_share` typically takes a comment and an optional URL/title/description.
            # It might not fully map to all UGC Posts API capabilities.
            # Example: linkedin_client.submit_share(comment=content, content_url=None, title=None, description=None)

            # Since `python3-linkedin` often targets older APIs or simpler use cases,
            # and the `create_post` method in the original code uses V2 `ugcPosts`,
            # it's often better to stick to the explicit V2 call for robust posting.
            # We'll keep the direct request for `create_post` as it directly maps to V2.

            # Fetch user's URN for the author field in UGC Posts.
            profile_data = await self._make_authenticated_request(
                access_token,
                "../userinfo"
            )
            person_urn = f"urn:li:person:{profile_data.get('sub')}"

            post_data = {
                "author": person_urn,
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
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Failed to create post: {str(e)}"
            )

    async def _get_certifications(self, params: Dict[str, Any]) -> ServiceResponse:
        """Get user's LinkedIn certifications. The SDK does not appear to have a direct method
        for certifications under `get_profile` or similar, so we'll use direct requests."""
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
            # LinkedIn's V2 API for profile data requires specific projections.
            # This endpoint is common for fetching structured profile elements.
            certifications_data = await self._make_authenticated_request(
                access_token,
                "me?projection=(certifications*(entityUrn,name,authority,startDate,endDate))"
            )
            # The 'me' endpoint returns a dictionary with various profile sections as keys.
            # We want the 'certifications' key.
            return ServiceResponse(
                success=True,
                data=certifications_data.get('certifications', {})
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return ServiceResponse(
                    success=False,
                    error="Permission denied. Your access token may not have the necessary permissions (e.g., 'r_basicprofile') for certifications. Also, specific profile fields might require special access or be limited."
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
        """Get user's LinkedIn courses. Similar to certifications, this is likely a direct request."""
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
                "me?projection=(courses*(entityUrn,name,authority))"
            )
            return ServiceResponse(
                success=True,
                data=courses_data.get('courses', {})
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return ServiceResponse(
                    success=False,
                    error="Permission denied. Your access token may not have the necessary permissions for courses. Also, specific profile fields might require special access or be limited."
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
        """Get user's LinkedIn job experience. Likely a direct request with projection."""
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
                "me?projection=(positions*(entityUrn,title,companyName,startDate,endDate,location))"
            )
            return ServiceResponse(
                success=True,
                data=experience_data.get('positions', {})
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return ServiceResponse(
                    success=False,
                    error="Permission denied. Your access token may not have the necessary permissions for job experience. Also, specific profile fields might require special access or be limited."
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

    async def _search_jobs(self, params: Dict[str, Any]) -> ServiceResponse:
        """Search for LinkedIn jobs, prioritizing the SDK's `search_job` method."""
        access_token = params.get("access_token")
        user_id = params.get("user_id", "default_user")
        title = params.get("title", "python")
        count = params.get("count", 2)
        location = params.get("location", "")
        company = params.get("company", "")

        if not access_token:
            stored_token = await get_valid_token(user_id)
            if not stored_token:
                return ServiceResponse(
                    success=False,
                    error="No valid stored token found. Please authenticate first."
                )
            access_token = stored_token.access_token

        try:
            linkedin_client = self._get_linkedin_client(access_token)

            # The python3-linkedin SDK's `search_job` method is designed for this.
            # It expects `selectors` and `params`.
            # Note: LinkedIn's job search API access is highly restricted and usually requires
            # specific partnership agreements. This method might not work for standard OAuth apps.

            # Selectors determine which fields of the job posting to return.
            # The structure `[{'jobs': ['id', ...]}]` is specific to the python3-linkedin SDK.
            selectors = [{'jobs': ['id', 'customer-job-code', 'posting-date', 'company', 'position']}]

            # Parameters for the search query.
            search_params = {
                'title': title,
                'count': count
            }

            if location:
                search_params['location'] = location
            if company:
                search_params['company'] = company

            jobs_data = linkedin_client.search_job(selectors=selectors, params=search_params)

            return ServiceResponse(
                success=True,
                data=jobs_data
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Job search failed via SDK: {str(e)}. Note: LinkedIn Job Search API access is highly restricted and likely requires specific partnership permissions."
            )

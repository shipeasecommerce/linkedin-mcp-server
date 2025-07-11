import os
import requests
from typing import Dict, Any, Optional
from database import store_token, get_valid_token

class LinkedInAPI:
    def __init__(self):
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
        self.base_url = "https://api.linkedin.com/v2"
    
    def get_auth_url(self, scope: str = "openid profile email w_member_social", state: str = "random_state") -> str:
        """Generate LinkedIn OAuth authorization URL"""
        return (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
            f"&scope={scope}"
        )
    
    async def exchange_code_for_token(self, code: str, user_id: str = "default_user") -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_info = response.json()
            await store_token(
                user_id=user_id,
                access_token=token_info["access_token"],
                expires_in=token_info.get("expires_in"),
                scope=token_info.get("scope")
            )
            return {"success": True, "data": token_info}
        else:
            return {"success": False, "error": f"Token exchange failed: {response.text}"}
    
    async def get_access_token(self, user_id: str) -> Optional[str]:
        """Get valid access token for user"""
        token_data = await get_valid_token(user_id)
        return token_data["access_token"] if token_data else None
    
    async def get_profile(self, user_id: str = "default_user") -> Dict[str, Any]:
        """Get LinkedIn profile with posting compliance information"""
        access_token = await self.get_access_token(user_id)
        if not access_token:
            return {"success": False, "error": "No valid access token found. Please authenticate first."}
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{self.base_url}/people/~", headers=headers)
        
        if response.status_code == 200:
            profile_data = response.json()
            # Add LinkedIn posting compliance information
            profile_data["posting_guidelines"] = {
                "max_post_length": 3000,
                "max_posts_per_day": 100,
                "max_mentions_per_post": 10,
                "rate_limit": "1 post per minute",
                "content_rules": [
                    "Keep content professional and authentic",
                    "Avoid spam and overly promotional content",
                    "Respect others' privacy and intellectual property",
                    "Use relevant hashtags (3-5 recommended)"
                ]
            }
            return {"success": True, "data": profile_data}
        else:
            return {"success": False, "error": f"Failed to get profile: {response.text}"}
    
    async def create_post(self, content: str, user_id: str = "default_user") -> Dict[str, Any]:
        """Create LinkedIn post with content validation"""
        # Content validation for LinkedIn compliance
        if len(content) > 3000:
            return {"success": False, "error": "Post content exceeds 3000 character limit"}
        
        if len(content.strip()) == 0:
            return {"success": False, "error": "Post content cannot be empty"}
        
        # Check for excessive mentions (LinkedIn limit: 10 per post)
        mention_count = content.count('@')
        if mention_count > 10:
            return {"success": False, "error": f"Too many mentions ({mention_count}). LinkedIn limit is 10 per post."}
        
        access_token = await self.get_access_token(user_id)
        if not access_token:
            return {"success": False, "error": "No valid access token found. Please authenticate first."}
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get user profile ID for posting
        profile_response = requests.get(f"{self.base_url}/people/~", headers=headers)
        if profile_response.status_code != 200:
            return {"success": False, "error": "Failed to get user profile for posting"}
        
        profile_data = profile_response.json()
        author_urn = profile_data.get("id")
        
        post_data = {
            "author": f"urn:li:person:{author_urn}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        
        response = requests.post(f"{self.base_url}/ugcPosts", json=post_data, headers=headers)
        
        if response.status_code == 201:
            post_result = response.json()
            return {
                "success": True,
                "data": {
                    "post_id": post_result.get("id"),
                    "post_url": f"https://www.linkedin.com/feed/update/{post_result.get('id')}",
                    "content": content,
                    "character_count": len(content),
                    "compliance_check": "passed"
                }
            }
        else:
            return {"success": False, "error": f"Failed to create post: {response.text}"}
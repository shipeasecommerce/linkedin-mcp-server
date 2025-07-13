import os
import sys
import requests
from typing import Dict, Any, Optional
from database import store_token, get_valid_token

class LinkedInAPI:
    def __init__(self):
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI")
        self.base_url = "https://api.linkedin.com/v2"
    
    def get_auth_url(self, scope: str = None, state: str = "random_state") -> str:
        """Generate LinkedIn OAuth authorization URL"""
        # Use fixed scopes that match the LinkedIn app configuration
        # Using only scopes available in the LinkedIn app
        fixed_scope = "openid profile email w_member_social"
        
        return (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&state={state}"
            f"&scope={fixed_scope}"
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
            await store_token(user_id, token_info)
            return {"success": True, "data": token_info}
        else:
            return {"success": False, "error": f"Token exchange failed: {response.text}"}
    
    async def get_access_token(self, user_id: str) -> Optional[str]:
        """Get valid access token for user"""
        token_data = await get_valid_token(user_id)
        return token_data.access_token if token_data else None
    
    async def get_education(self, user_id: str = "default_user") -> Dict[str, Any]:
        """Get LinkedIn education/study information - LIMITED ACCESS with current scopes"""
        access_token = await self.get_access_token(user_id)
        if not access_token:
            return {"success": False, "error": "No valid access token found. Please authenticate first."}
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202405",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Try to get education data - this will likely fail with current scopes
        try:
            education_url = f"{self.base_url}/me?projection=(educations*(entityUrn,schoolName,fieldOfStudy,degree,startDate,endDate))"
            response = requests.get(education_url, headers=headers)
            
            if response.status_code == 200:
                education_data = response.json()
                return {"success": True, "data": education_data.get("educations", {})}
            else:
                # Check if it's a permission error
                if response.status_code == 403:
                    return {
                        "success": False, 
                        "error": "Education data access denied. LinkedIn requires additional permissions (r_liteprofile/r_basicprofile) or Partner Program access for detailed profile data.",
                        "scope_issue": True
                    }
                return {"success": False, "error": f"Failed to get education data: {response.text}"}
        except Exception as e:
            return {"success": False, "error": f"Education fetch failed: {str(e)}"}

    async def get_courses(self, user_id: str = "default_user") -> Dict[str, Any]:
        """Get LinkedIn courses information - LIMITED ACCESS with current scopes"""
        access_token = await self.get_access_token(user_id)
        if not access_token:
            return {"success": False, "error": "No valid access token found. Please authenticate first."}
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202405",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Try to get courses data - this will likely fail with current scopes
        try:
            courses_url = f"{self.base_url}/me?projection=(courses*(entityUrn,name,authority,startDate,endDate))"
            response = requests.get(courses_url, headers=headers)
            
            if response.status_code == 200:
                courses_data = response.json()
                return {"success": True, "data": courses_data.get("courses", {})}
            else:
                # Check if it's a permission error
                if response.status_code == 403:
                    return {
                        "success": False, 
                        "error": "Courses data access denied. LinkedIn requires additional permissions (r_liteprofile/r_basicprofile) or Partner Program access for detailed profile data.",
                        "scope_issue": True
                    }
                return {"success": False, "error": f"Failed to get courses data: {response.text}"}
        except Exception as e:
            return {"success": False, "error": f"Courses fetch failed: {str(e)}"}

    async def get_profile(self, user_id: str = "default_user") -> Dict[str, Any]:
        """Get LinkedIn profile with posting compliance information"""
        access_token = await self.get_access_token(user_id)
        if not access_token:
            return {"success": False, "error": "No valid access token found. Please authenticate first."}
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202405",  # Specify API version
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Use the LinkedIn OpenID userinfo endpoint which works with our scopes
        profile_url = f"{self.base_url}/userinfo"
        print(f"🔗 Making request to: {profile_url}", file=sys.stderr)
        print(f"🔑 Headers: {headers}", file=sys.stderr)
        
        response = requests.get(profile_url, headers=headers)
        
        print(f"📡 Response Status: {response.status_code}", file=sys.stderr)
        print(f"📡 Response Headers: {dict(response.headers)}", file=sys.stderr)
        
        if response.status_code == 200:
            profile_data = response.json()
            print(f"📊 Raw LinkedIn Response: {profile_data}", file=sys.stderr)
            
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
            print(f"📊 Final Profile Data with Guidelines: {profile_data}", file=sys.stderr)
            return {"success": True, "data": profile_data}
        else:
            print(f"❌ Error Response: {response.text}", file=sys.stderr)
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
            "Content-Type": "application/json",
            "LinkedIn-Version": "202405",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Get user profile ID for posting using correct userinfo endpoint
        profile_url = f"{self.base_url}/userinfo"
        profile_response = requests.get(profile_url, headers=headers)
        if profile_response.status_code != 200:
            return {"success": False, "error": "Failed to get user profile for posting"}
        
        profile_data = profile_response.json()
        author_urn = profile_data.get("sub")
        
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
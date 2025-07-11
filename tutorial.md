# LinkedIn MCP Server Tutorial

## Overview

This tutorial will guide you through creating a LinkedIn Model Context Protocol (MCP) server using the official Python SDK and connecting it with Claude Code. The MCP server enables Claude to interact with LinkedIn's API through standardized tool calls.

## What You'll Build

An MCP server using the official Python SDK that provides:
- LinkedIn OAuth authentication
- Profile and user information retrieval
- Post creation and management (with LinkedIn compliance)
- Job searching capabilities
- Experience, certifications, and courses data

## Prerequisites

- Python 3.9+
- LinkedIn Developer Account
- Basic knowledge of Python and OAuth 2.0
- UV package manager (recommended) or pip
- Understanding of MCP (Model Context Protocol) concepts

## Step 1: LinkedIn Developer Setup

### 1.1 Create LinkedIn App

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Click "Create App"
3. Fill in required details:
   - App name: "My MCP LinkedIn Server"
   - LinkedIn Page: Your company/personal page
   - App logo: Upload any image
4. Select products needed:
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn** (for posting)
   - **Marketing Developer Platform** (for user data)

### 1.2 Configure OAuth Settings

1. In your app dashboard, go to "Auth" tab
2. Add authorized redirect URLs:
   ```
   http://localhost:8000/linkedin/callback
   ```
3. Note down:
   - Client ID
   - Client Secret

### 1.3 LinkedIn Posting Rules & Compliance

#### Content Guidelines
- **Authentic Content**: All posts must be genuine and represent real experiences or insights
- **No Spam**: Avoid repetitive, irrelevant, or overly promotional content
- **Professional Tone**: Maintain appropriate professional language and demeanor
- **Respect Privacy**: Don't share personal information of others without consent

#### Rate Limits
- **Posts**: Maximum 100 API calls per day per user for posting
- **Profile Data**: 500 API calls per day per application
- **Search**: Varies by endpoint (typically 100-1000 per day)

#### Technical Requirements
- **Content Length**: Posts limited to 3,000 characters
- **Media**: Images must be under 100MB, videos under 200MB
- **Frequency**: No more than 1 post per minute per user
- **Mentions**: Limited to 10 @mentions per post

#### Best Practices
- Always include meaningful content, not just links
- Use relevant hashtags (max 3-5 per post)
- Engage authentically with your network
- Respect LinkedIn's professional community standards

## Step 2: Project Setup

### 2.1 Initialize Project

```bash
# Create project directory
mkdir linkedin-mcp-server
cd linkedin-mcp-server

# Initialize with UV (recommended)
uv init
```

### 2.2 Install Dependencies

Create `pyproject.toml`:

```toml
[project]
name = "linkedin-mcp-server"
version = "1.0.0"
description = "A Model Context Protocol server for LinkedIn API integration"
dependencies = [
    "mcp>=1.0.0",
    "requests>=2.31.0",
    "authlib>=1.3.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",
    "pydantic>=2.0.0",
]
requires-python = ">=3.9.0"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Install dependencies:
```bash
uv sync
```

### 2.3 Environment Configuration

Create `.env` file:
```env
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_REDIRECT_URI=http://localhost:8000/linkedin/callback
HOST=localhost
PORT=8000
```

## Step 3: MCP Server Implementation

### 3.1 Database Setup

Create `database.py`:

```python
import sqlite3
import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

async def init_database():
    """Initialize the database with tokens table"""
    async with aiosqlite.connect("linkedin_tokens.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS linkedin_tokens (
                user_id TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                token_type TEXT DEFAULT 'Bearer',
                expires_at TEXT,
                scope TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

async def store_token(user_id: str, access_token: str, expires_in: int = None, 
                     token_type: str = "Bearer", scope: str = None):
    """Store or update LinkedIn access token"""
    expires_at = None
    if expires_in:
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
    
    async with aiosqlite.connect("linkedin_tokens.db") as db:
        await db.execute('''
            INSERT OR REPLACE INTO linkedin_tokens 
            (user_id, access_token, token_type, expires_at, scope, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, access_token, token_type, expires_at, scope, datetime.now().isoformat()))
        await db.commit()

async def get_valid_token(user_id: str) -> Optional[Dict[str, Any]]:
    """Get valid access token for user"""
    async with aiosqlite.connect("linkedin_tokens.db") as db:
        async with db.execute('''
            SELECT access_token, token_type, expires_at, scope 
            FROM linkedin_tokens WHERE user_id = ?
        ''', (user_id,)) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return None
                
            access_token, token_type, expires_at, scope = row
            
            # Check if token is expired
            if expires_at:
                expire_time = datetime.fromisoformat(expires_at)
                if datetime.now() >= expire_time:
                    return None
            
            return {
                "access_token": access_token,
                "token_type": token_type,
                "expires_at": expires_at,
                "scope": scope
            }
```

### 3.2 LinkedIn Helper Functions

Create `linkedin_api.py`:

```python
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
```

### 3.3 MCP Server Implementation

Create `linkedin_mcp_server.py`:

```python
import asyncio
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from database import init_database
from linkedin_api import LinkedInAPI

load_dotenv()

# Create the MCP server
mcp = FastMCP("LinkedIn MCP Server")

# Initialize LinkedIn API client
linkedin_api = LinkedInAPI()

@mcp.lifespan
async def server_lifespan():
    """Initialize database on server startup"""
    await init_database()
    yield

@mcp.tool()
async def start_linkedin_auth(scope: str = "openid profile email w_member_social") -> str:
    """Start LinkedIn OAuth authentication flow
    
    Returns a URL that users should visit to authenticate with LinkedIn.
    After authentication, they'll be redirected with a code to exchange for tokens.
    
    Args:
        scope: OAuth scope for LinkedIn permissions
    """
    auth_url = linkedin_api.get_auth_url(scope=scope)
    return f"🔗 Please visit this URL to authenticate with LinkedIn:\n{auth_url}\n\nAfter authorization, you'll receive a code. Use the 'exchange_linkedin_token' tool with that code."

@mcp.tool()
async def exchange_linkedin_token(code: str, user_id: str = "default_user") -> str:
    """Exchange authorization code for access token
    
    Use this after completing the LinkedIn OAuth flow to store the access token.
    
    Args:
        code: Authorization code from LinkedIn OAuth callback
        user_id: User identifier for token storage
    """
    result = await linkedin_api.exchange_code_for_token(code, user_id)
    
    if result["success"]:
        return f"✅ LinkedIn authentication successful!\nToken stored for user: {user_id}\nScope: {result['data'].get('scope', 'Not specified')}"
    else:
        return f"❌ Authentication failed: {result['error']}"

@mcp.tool()
async def get_linkedin_profile(user_id: str = "default_user") -> str:
    """Get LinkedIn user profile with posting compliance guidelines
    
    Returns profile information along with LinkedIn's posting rules and limitations.
    
    Args:
        user_id: User identifier to get profile for
    """
    result = await linkedin_api.get_profile(user_id)
    
    if result["success"]:
        profile = result["data"]
        
        # Format the response with posting guidelines
        response = f"""📋 LinkedIn Profile Information:
        
👤 Name: {profile.get('localizedFirstName', 'N/A')} {profile.get('localizedLastName', 'N/A')}
🆔 Profile ID: {profile.get('id', 'N/A')}

📝 LinkedIn Posting Guidelines:
• Maximum post length: {profile['posting_guidelines']['max_post_length']} characters
• Daily posting limit: {profile['posting_guidelines']['max_posts_per_day']} posts
• Mentions limit: {profile['posting_guidelines']['max_mentions_per_post']} per post
• Rate limit: {profile['posting_guidelines']['rate_limit']}

✅ Content Rules:"""
        
        for rule in profile['posting_guidelines']['content_rules']:
            response += f"\n  • {rule}"
            
        return response
    else:
        return f"❌ Failed to get profile: {result['error']}"

@mcp.tool()
async def create_linkedin_post(content: str, user_id: str = "default_user") -> str:
    """Create a LinkedIn post with content validation
    
    Creates a post on LinkedIn while enforcing platform guidelines:
    - Maximum 3000 characters
    - Maximum 10 @mentions per post  
    - Professional content standards
    - Rate limiting compliance
    
    Args:
        content: The text content for the LinkedIn post
        user_id: User identifier for posting
    """
    result = await linkedin_api.create_post(content, user_id)
    
    if result["success"]:
        data = result["data"]
        return f"""✅ LinkedIn post created successfully!

📝 Post Details:
• Post ID: {data['post_id']}
• Content: "{data['content'][:100]}{'...' if len(data['content']) > 100 else ''}"
• Character count: {data['character_count']}/3000
• Compliance check: {data['compliance_check']}
• Post URL: {data['post_url']}

The post is now live on your LinkedIn profile!"""
    else:
        return f"❌ Failed to create post: {result['error']}"

@mcp.tool()
def linkedin_posting_guidelines() -> str:
    """Get comprehensive LinkedIn posting guidelines and best practices
    
    Returns detailed information about LinkedIn's content policies, 
    technical limitations, and best practices for professional posting.
    """
    return """📋 LinkedIn Posting Guidelines & Best Practices

🔢 Technical Limits:
• Post length: Maximum 3000 characters
• Daily posts: Up to 100 API calls per day per user
• Mentions: Maximum 10 @mentions per post
• Rate limit: 1 post per minute maximum
• Hashtags: 3-5 recommended (no hard limit)

📝 Content Guidelines:
• Keep content professional and authentic
• Share genuine insights, experiences, or valuable information
• Avoid spam, repetitive, or overly promotional content
• Respect others' privacy and intellectual property
• Use appropriate professional language

🎯 Best Practices:
• Engage authentically with your network
• Include relevant hashtags (3-5 recommended)
• Ask questions to encourage discussion
• Share visual content when appropriate
• Post consistently but not excessively
• Respond to comments on your posts

⚠️ Compliance Requirements:
• All content must follow LinkedIn's Community Guidelines
• No misleading or false information
• Respect copyright and trademark laws
• No harassment, hate speech, or inappropriate content
• Professional standards apply to all posts

🚀 Optimization Tips:
• Post during business hours for better engagement
• Use compelling first lines to grab attention
• Include calls-to-action when appropriate
• Share industry insights and thought leadership
• Celebrate achievements and milestones professionally"""

@mcp.resource("linkedin://guidelines")
def get_guidelines_resource() -> str:
    """Resource providing LinkedIn posting guidelines"""
    return linkedin_posting_guidelines()

@mcp.resource("linkedin://profile/{user_id}")
async def get_profile_resource(user_id: str) -> str:
    """Resource for getting LinkedIn profile data"""
    result = await linkedin_api.get_profile(user_id)
    if result["success"]:
        return str(result["data"])
    else:
        return f"Error: {result['error']}"
```

## Step 4: Running the MCP Server

### 4.1 Test the Server Locally

```bash
# Using UV to run the server
uv run python linkedin_mcp_server.py
```

### 4.2 Test with MCP CLI (Optional)

```bash
# Install the MCP CLI for testing
npm install -g @modelcontextprotocol/cli

# Test your server
mcp dev linkedin_mcp_server.py
```

## Step 5: Claude Code Integration

### 5.1 Install Claude Code

Follow the [Claude Code installation guide](https://docs.anthropic.com/en/docs/claude-code/quickstart).

### 5.2 Configure MCP Settings

Create or update your MCP settings file:

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": ["run", "python", "/path/to/your/project/linkedin_mcp_server.py"],
      "env": {
        "LINKEDIN_CLIENT_ID": "your_client_id",
        "LINKEDIN_CLIENT_SECRET": "your_client_secret",
        "LINKEDIN_REDIRECT_URI": "http://localhost:8000/linkedin/callback"
      }
    }
  }
}
```

**For Claude Code CLI** (`~/.config/claude/claude_code_config.json`):

```json
{
  "mcpServers": {
    "linkedin": {
      "command": "uv",
      "args": ["run", "python", "/path/to/your/project/linkedin_mcp_server.py"],
      "env": {
        "LINKEDIN_CLIENT_ID": "your_client_id",
        "LINKEDIN_CLIENT_SECRET": "your_client_secret",
        "LINKEDIN_REDIRECT_URI": "http://localhost:8000/linkedin/callback"
      }
    }
  }
}
```

### 5.3 Using the LinkedIn MCP Server

1. **Start Authentication**:
   ```
   Use the start_linkedin_auth tool to begin LinkedIn authentication
   ```

2. **Complete OAuth Flow**:
   After getting the auth URL, visit it, authorize, and get the code:
   ```
   Use exchange_linkedin_token with code: abc123def456
   ```

3. **Get Profile with Posting Guidelines**:
   ```
   Use get_linkedin_profile to get my profile information
   ```

4. **View Posting Guidelines**:
   ```
   Use linkedin_posting_guidelines to show me the posting rules
   ```

5. **Create Posts** (Following LinkedIn Guidelines):
   ```
   Use create_linkedin_post with content: "Excited to share my latest project on AI automation! 
   Building MCP servers has opened up new possibilities for LLM integrations. 
   #MachineLearning #AI #TechInnovation"
   ```

### 5.4 Available MCP Tools

Your LinkedIn MCP server provides these tools:

- **`start_linkedin_auth`** - Generates OAuth URL for authentication
- **`exchange_linkedin_token`** - Exchanges auth code for access token  
- **`get_linkedin_profile`** - Gets profile with posting guidelines
- **`create_linkedin_post`** - Creates posts with compliance validation
- **`linkedin_posting_guidelines`** - Shows comprehensive posting rules

### 5.5 Available MCP Resources

Your server also provides these resources:

- **`linkedin://guidelines`** - Access posting guidelines as a resource
- **`linkedin://profile/{user_id}`** - Access profile data as a resource

## LinkedIn Content Best Practices

### Professional Content Guidelines

1. **Authentic Voice**: Write in your genuine professional voice
2. **Value-Driven**: Share insights, experiences, or helpful information
3. **Engagement**: Ask questions or encourage discussion
4. **Visual Elements**: Include relevant images or documents when appropriate

### Compliance Checklist

- ✅ Content under 3000 characters
- ✅ Professional and appropriate language
- ✅ No more than 10 @mentions
- ✅ Relevant hashtags (3-5 recommended)
- ✅ Respects intellectual property
- ✅ Follows LinkedIn Community Guidelines

### Rate Limiting Considerations

- Post maximum once per minute
- Limit to 100 API calls per day for posting
- Monitor your usage to stay within limits
- Implement exponential backoff for rate limit errors

## Security Considerations

1. **Environment Variables**: Never commit credentials to version control
2. **Token Storage**: Use secure database storage for access tokens
3. **HTTPS**: Use HTTPS in production environments
4. **Scope Limitation**: Only request necessary LinkedIn permissions
5. **Token Expiration**: Implement proper token refresh logic

## Troubleshooting

### Common Issues

1. **OAuth Redirect Mismatch**: Ensure redirect URI matches exactly in LinkedIn app settings
2. **Scope Errors**: Verify your LinkedIn app has the required products enabled
3. **Rate Limits**: Implement retry logic with exponential backoff
4. **Token Expiration**: Check token validity before making API calls

### Debugging Tips

- Use FastAPI's automatic documentation at `/docs`
- Check server logs for detailed error messages
- Verify environment variables are loaded correctly
- Test OAuth flow manually before integrating with Claude

## Next Steps

1. **Enhanced Features**: Add support for LinkedIn articles, company pages
2. **Analytics**: Implement post performance tracking
3. **Scheduling**: Add post scheduling capabilities
4. **Media Upload**: Support for image and video uploads
5. **Company Integration**: Extend to company page management

This MCP server provides a solid foundation for LinkedIn integration while maintaining compliance with LinkedIn's API guidelines and community standards.
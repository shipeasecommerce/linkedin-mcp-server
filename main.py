import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from database import init_database
from linkedin_api import LinkedInAPI

load_dotenv()

# Create the MCP server
mcp = FastMCP("LinkedIn MCP Server")

# Expose as app for uvicorn
app = mcp

# Initialize LinkedIn API client
linkedin_api = LinkedInAPI()

# Database initialization flag
_database_initialized = False

async def ensure_database_initialized():
    """Ensure database is initialized before using tools"""
    global _database_initialized
    if not _database_initialized:
        await init_database()
        _database_initialized = True

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
    await ensure_database_initialized()
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
    await ensure_database_initialized()
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
    await ensure_database_initialized()
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
    await ensure_database_initialized()
    result = await linkedin_api.get_profile(user_id)
    if result["success"]:
        return str(result["data"])
    else:
        return f"Error: {result['error']}"

if __name__ == "__main__":
    # Check command line arguments for transport mode
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run the server using stdio transport for Claude integration
        print("Starting MCP server in stdio mode for Claude integration...", file=sys.stderr)
        mcp.run()
    else:
        # Default: provide instructions for both modes
        print("LinkedIn MCP Server")
        print("===================")
        print()
        print("Usage:")
        print("  For Claude integration (stdio):  python main.py --stdio")
        print("  For HTTP server (uvicorn):       uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print()
        print("To run in stdio mode now, use: python main.py --stdio")
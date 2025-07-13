import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Global variables
_database_initialized = False

async def ensure_database_initialized():
    """Ensure database is initialized before using tools"""
    global _database_initialized
    if not _database_initialized:
        try:
            from database import init_database
            await init_database()
            _database_initialized = True
            print("Database initialized successfully", file=sys.stderr)
        except Exception as e:
            print(f"Database initialization failed: {e}", file=sys.stderr)
            # Continue without failing - database will be created on first use
            pass

def create_mcp_server():
    """Create and configure MCP server with all tools"""
    print("Creating MCP server...", file=sys.stderr)
    from mcp.server.fastmcp import FastMCP
    from linkedin_api import LinkedInAPI
    
    # Create FastMCP server
    mcp = FastMCP("LinkedIn MCP Server")
    
    linkedin_api = LinkedInAPI()
    print("MCP server components initialized", file=sys.stderr)

    @mcp.tool()
    async def start_linkedin_auth() -> str:
        """Start LinkedIn OAuth authentication flow - Step 1 of 2

        This is the first step of LinkedIn authentication. It generates an authorization URL
        that you must visit in your browser. This tool completes immediately.

        After visiting the URL and authorizing, use 'exchange_linkedin_token' tool.

        Note: Uses fixed scopes configured in the LinkedIn app for security.
        """
        auth_url = linkedin_api.get_auth_url()
        return f"""🔗 STEP 1: LinkedIn Authentication Started

Please visit this URL in your browser to authorize the application:
{auth_url}

📝 NEXT STEPS:
1. Click the URL above or copy/paste it into your browser
2. Log in to LinkedIn and authorize the application
3. You'll be redirected to a callback URL with a 'code' parameter
4. Copy that code and use the 'exchange_linkedin_token' tool

⏱️ This step is now complete. The authorization URL is ready for you to visit."""

    @mcp.tool()
    async def exchange_linkedin_token(code: str, user_id: str = "default_user") -> str:
        """Complete LinkedIn OAuth authentication flow - Step 2 of 2

        Use this after visiting the auth URL from 'start_linkedin_auth' and getting
        the authorization code from the callback URL.

        Args:
            code: Authorization code from LinkedIn OAuth callback URL
            user_id: User identifier for token storage (default: "default_user")
        """
        # Database will be initialized automatically by the token storage
        result = await linkedin_api.exchange_code_for_token(code, user_id)

        if result["success"]:
            return f"✅ LinkedIn authentication successful!\nToken stored for user: {user_id}\nScope: {result['data'].get('scope', 'Not specified')}"
        else:
            return f"❌ Authentication failed: {result['error']}"

    @mcp.tool()
    async def check_linkedin_auth_status(user_id: str = "default_user") -> str:
        """Check if LinkedIn authentication is complete for a user

        This tool checks if a valid LinkedIn access token exists for the specified user.

        Args:
            user_id: User identifier to check (default: "default_user")
        """
        try:
            from database import get_valid_token
            token = await get_valid_token(user_id)
            if token:
                return f"✅ LinkedIn authentication is active for user: {user_id}\n🕒 Token expires: {token.expires_at or 'No expiration'}\n📧 Email: {token.email or 'Not available'}"
            else:
                return f"❌ No valid LinkedIn authentication found for user: {user_id}\n\n💡 Use 'start_linkedin_auth' to begin the authentication process."
        except Exception as e:
            return f"❌ Error checking authentication status: {str(e)}"

    @mcp.tool()
    async def get_linkedin_profile(user_id: str = "default_user") -> str:
        """Get LinkedIn user profile with posting compliance guidelines

        Returns profile information along with LinkedIn's posting rules and limitations.

        Args:
            user_id: User identifier to get profile for
        """
        # Database will be initialized if needed
        result = await linkedin_api.get_profile(user_id)
        
        # Log the raw API response for debugging
        print(f"🔍 LinkedIn API Response: {result}", file=sys.stderr)

        if result["success"]:
            profile = result["data"]
            
            # Log the profile data structure
            print(f"📊 Profile Data Keys: {list(profile.keys()) if isinstance(profile, dict) else 'Not a dict'}", file=sys.stderr)
            print(f"📊 Full Profile Data: {profile}", file=sys.stderr)

            # Check different possible field names for name information
            first_name = (profile.get('localizedFirstName') or 
                         profile.get('firstName') or 
                         profile.get('given_name') or 
                         'N/A')
            
            last_name = (profile.get('localizedLastName') or 
                        profile.get('lastName') or 
                        profile.get('family_name') or 
                        'N/A')
            
            profile_id = (profile.get('id') or 
                         profile.get('sub') or 
                         'N/A')
            
            # Log what we found
            print(f"🔍 Extracted Data - First: {first_name}, Last: {last_name}, ID: {profile_id}", file=sys.stderr)

            # Format the response with posting guidelines
            response = f"""📋 LinkedIn Profile Information:

👤 Name: {first_name} {last_name}
🆔 Profile ID: {profile_id}

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
    async def get_linkedin_education(user_id: str = "default_user") -> str:
        """Get LinkedIn education/study information

        Retrieves education data including schools, degrees, fields of study, and dates.

        Args:
            user_id: User identifier to get education for
        """
        result = await linkedin_api.get_education(user_id)

        if result["success"]:
            education_data = result["data"]
            if not education_data:
                return "📚 No education information found in your LinkedIn profile."

            response = "📚 LinkedIn Education Information:\n\n"
            for edu in education_data.get("elements", []):
                school = edu.get("schoolName", "Unknown School")
                degree = edu.get("degree", "N/A")
                field = edu.get("fieldOfStudy", "N/A")
                start_date = edu.get("startDate", {})
                end_date = edu.get("endDate", {})

                response += f"🏫 School: {school}\n"
                response += f"🎓 Degree: {degree}\n"
                response += f"📖 Field of Study: {field}\n"

                if start_date:
                    response += f"📅 Start: {start_date.get('year', '')}\n"
                if end_date:
                    response += f"📅 End: {end_date.get('year', '')}\n"
                response += "\n"

            return response
        else:
            if result.get("scope_issue"):
                return f"""❌ Education data access restricted by LinkedIn

🔒 **Access Limitation**: LinkedIn has restricted detailed profile data access.

💡 **What you need**:
1. **LinkedIn Partner Program** access, OR
2. Additional scopes (`r_liteprofile`, `r_basicprofile`) - but these may not be available to standard apps

📋 **Current scopes**: `openid`, `profile`, `email`, `w_member_social`

🌐 **Alternative**: Only basic profile info is available via the userinfo endpoint."""
            else:
                return f"❌ Failed to get education data: {result['error']}"

    @mcp.tool()
    async def get_linkedin_courses(user_id: str = "default_user") -> str:
        """Get LinkedIn courses information

        Retrieves courses and certifications data including course names, authorities, and dates.

        Args:
            user_id: User identifier to get courses for
        """
        result = await linkedin_api.get_courses(user_id)

        if result["success"]:
            courses_data = result["data"]
            if not courses_data:
                return "📋 No courses information found in your LinkedIn profile."

            response = "📋 LinkedIn Courses Information:\n\n"
            for course in courses_data.get("elements", []):
                name = course.get("name", "Unknown Course")
                authority = course.get("authority", "N/A")
                start_date = course.get("startDate", {})
                end_date = course.get("endDate", {})

                response += f"📚 Course: {name}\n"
                response += f"🏛️ Authority: {authority}\n"

                if start_date:
                    response += f"📅 Start: {start_date.get('year', '')}\n"
                if end_date:
                    response += f"📅 End: {end_date.get('year', '')}\n"
                response += "\n"

            return response
        else:
            if result.get("scope_issue"):
                return f"""❌ Courses data access restricted by LinkedIn

🔒 **Access Limitation**: LinkedIn has restricted detailed profile data access.

💡 **What you need**:
1. **LinkedIn Partner Program** access, OR
2. Additional scopes (`r_liteprofile`, `r_basicprofile`) - but these may not be available to standard apps

📋 **Current scopes**: `openid`, `profile`, `email`, `w_member_social`

🌐 **Alternative**: Only basic profile info is available via the userinfo endpoint."""
            else:
                return f"❌ Failed to get courses data: {result['error']}"

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

    print("MCP server fully configured with all tools", file=sys.stderr)
    return mcp


def create_callback_server():
    """Create a simple FastAPI server for OAuth callback"""
    from fastapi import FastAPI, Query
    from fastapi.responses import HTMLResponse
    from linkedin_api import LinkedInAPI
    
    app = FastAPI(title="LinkedIn OAuth Callback")
    linkedin_api = LinkedInAPI()
    
    @app.get("/linkedin/callback")
    async def linkedin_callback(
        code: str = Query(None), 
        error: str = Query(None), 
        error_description: str = Query(None), 
        state: str = Query(None),
        user_id: str = Query("default_user")
    ):
        """Handle LinkedIn OAuth callback"""
        if error:
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head><title>LinkedIn Authentication Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: red;">❌ LinkedIn OAuth Error</h1>
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {error_description or 'No description provided'}</p>
                    <p>Please try the authentication process again.</p>
                </body>
                </html>
                """,
                status_code=400
            )
        
        if not code:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head><title>LinkedIn Authentication Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: red;">❌ No Authorization Code</h1>
                    <p>No authorization code was received from LinkedIn.</p>
                    <p>Please try the authentication process again.</p>
                </body>
                </html>
                """,
                status_code=400
            )
        
        # Exchange code for token
        await ensure_database_initialized()
        result = await linkedin_api.exchange_code_for_token(code, user_id)
        
        if not result["success"]:
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head><title>LinkedIn Token Exchange Failed</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: red;">❌ Token Exchange Failed</h1>
                    <p><strong>Error:</strong> {result['error']}</p>
                    <p>Please try the authentication process again.</p>
                </body>
                </html>
                """,
                status_code=500
            )
        
        # Success response
        token_data = result['data']
        return HTMLResponse(
            content=f"""
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
                    <p><strong>User ID:</strong> {user_id}</p>
                    <p><strong>Token Type:</strong> {token_data.get('token_type', 'Bearer')}</p>
                    <p><strong>Scope:</strong> {token_data.get('scope', 'Not specified')}</p>
                    <hr>
                    <p>You can now close this window. Your LinkedIn token has been securely stored and you can use LinkedIn MCP tools.</p>
                </div>
                <script>
                    // Try to close the window after 3 seconds
                    setTimeout(() => {{
                        if (window.opener) {{
                            window.close();
                        }} else {{
                            document.body.innerHTML += '<p style="color: blue; margin-top: 20px;">You can now close this tab manually.</p>';
                        }}
                    }}, 3000);
                </script>
            </body>
            </html>
            """
        )
    
    return app

# Create app instance for uvicorn import
app = create_callback_server()

if __name__ == "__main__":
    # Check command line arguments for transport mode
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run MCP server only (stdio mode for Claude) - no HTTP
        print("Starting MCP server in stdio mode for Claude integration...", file=sys.stderr)
        mcp = create_mcp_server()
        mcp.run()
    else:
        # Default: Run callback server for OAuth
        import uvicorn
        print("Starting LinkedIn OAuth callback server...", file=sys.stderr)
        print("LinkedIn OAuth callback available at: http://localhost:8000/linkedin/callback", file=sys.stderr)
        print("For stdio mode (Claude integration): python main.py --stdio", file=sys.stderr)
        print("Use LinkedIn MCP tools through Claude or other MCP clients", file=sys.stderr)
        
        app = create_callback_server()
        uvicorn.run(app, host="0.0.0.0", port=8000)

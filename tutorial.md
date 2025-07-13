# LinkedIn MCP Server Tutorial

A complete guide to setting up and using the LinkedIn Model Context Protocol (MCP) server with Claude Code and Claude Desktop.

## Overview

This LinkedIn MCP server enables AI assistants to interact with LinkedIn through standardized tool calls. It supports OAuth authentication, profile data retrieval, post creation, and other LinkedIn features.

## Prerequisites

- Python 3.8+
- uv package manager
- LinkedIn Developer App with OAuth configured
- Claude Code CLI or Claude Desktop app

## Step 1: LinkedIn Developer Setup

1. Create a LinkedIn Developer Application at [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Configure OAuth 2.0 settings:
   - **Redirect URI**: `http://localhost:8000/linkedin/callback`
   - **Products**: Enable "Sign In with LinkedIn using OpenID Connect" and "Share on LinkedIn"
3. Note your `Client ID` and `Client Secret`

## Step 2: Environment Configuration

Create a `.env` file in your project directory:

```bash
LINKEDIN_CLIENT_ID=your_client_id_here
LINKEDIN_CLIENT_SECRET=your_client_secret_here
LINKEDIN_REDIRECT_URI=http://localhost:8000/linkedin/callback
```

## Step 3: Install Dependencies

```bash
# Install dependencies with uv
npm run install
# or
uv sync
```

## Step 4: Setup MCP Integration

### For Claude Code CLI

Add the MCP server to Claude Code:

```bash
claude mcp add-json linkedin-mcp '{"type":"stdio","command":"/Users/ronnyfreites/.local/bin/uv","args":["--directory", "/Users/ronnyfreites/projects/linkedin-mcp", "run", "python", "main.py", "--stdio"]}'
```

### For Claude Desktop App

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "linkedin-mcp": {
      "command": "uv",
      "args": [
        "--directory", 
        "/path/to/your/linkedin-mcp", 
        "run", 
        "python", 
        "main.py", 
        "--stdio"
      ],
      "env": {
        "LINKEDIN_CLIENT_ID": "your_client_id_here",
        "LINKEDIN_CLIENT_SECRET": "your_client_secret_here",
        "LINKEDIN_REDIRECT_URI": "http://localhost:8000/linkedin/callback"
      }
    }
  }
}
```

## Step 5: Authentication Flow

1. **Start OAuth flow**:
   ```
   Ask Claude: "Start LinkedIn authentication"
   ```

2. **Visit the provided URL** in your browser to authorize the application

3. **Exchange the authorization code**:
   ```
   Ask Claude: "Exchange the LinkedIn auth code: YOUR_CODE_HERE"
   ```

## Step 6: Available Features

### Profile Information
```
"Get my LinkedIn profile"
```

### Create Posts
```
"Create a LinkedIn post about [your topic]"
```

### Get Guidelines
```
"Show LinkedIn posting guidelines"
```

### Check Authentication
```
"Check LinkedIn auth status"
```

## Available MCP Tools

- `start_linkedin_auth` - Generate OAuth authorization URL
- `exchange_linkedin_token` - Exchange auth code for access token
- `check_linkedin_auth_status` - Verify authentication status
- `get_linkedin_profile` - Retrieve profile information
- `create_linkedin_post` - Create and publish posts
- `linkedin_posting_guidelines` - View content guidelines

## Troubleshooting

### Common Issues

1. **OAuth Redirect Mismatch**: Ensure redirect URI matches exactly in LinkedIn app settings
2. **Permission Errors**: Verify LinkedIn app has required products enabled
3. **Token Expiration**: Tokens expire after 60 days, re-authenticate when needed
4. **Rate Limits**: LinkedIn allows 1 post per minute, 100 posts per day

### Testing the Server

Test locally with HTTP endpoints:
```bash
# Start OAuth server
python main.py

# Visit http://localhost:8000/docs for Swagger UI
```

Test MCP functionality:
```bash
# Start MCP server
python main.py --stdio

# Test with MCP CLI
npm install -g @modelcontextprotocol/cli
mcp dev main.py --stdio
```

## Next Steps

- Explore additional LinkedIn API endpoints
- Implement content scheduling
- Add analytics and engagement tracking
- Create custom post templates

For more details, see the [LinkedIn API documentation](https://docs.microsoft.com/en-us/linkedin/) and [MCP specification](https://spec.modelcontextprotocol.io/).

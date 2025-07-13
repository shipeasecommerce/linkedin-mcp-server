# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LinkedIn Model Context Protocol (MCP) server that enables AI assistants to interact with LinkedIn's API through standardized tool calls. The server provides both HTTP REST endpoints and MCP protocol integration for LinkedIn OAuth authentication, profile data retrieval, post creation, and other LinkedIn features.

## Architecture

**Simplified Unified Architecture:**
- `main.py` - FastMCP server with unified MCP tools and OAuth callback server
- `linkedin_api.py` - Direct LinkedIn API wrapper using requests
- `database.py` - SQLAlchemy-based token storage with async SQLite

**Two Server Modes:**
1. **OAuth Callback Server** (default) - FastAPI server for LinkedIn OAuth authentication flow
2. **MCP Server** (--stdio) - FastMCP server for Claude/MCP client integration

## Development Commands

**Start the server:**
```bash
# OAuth callback server (default)
python main.py

# MCP server for Claude integration  
python main.py --stdio

# Alternative with uvicorn (OAuth callback server)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Package management:**
```bash
npm run install        # Install dependencies with uv
npm run install-dev    # Install with dev dependencies
```

**Code quality:**
```bash
npm run lint           # Run ruff linting
npm run format         # Format code with ruff
npm run test           # Run pytest tests
npm run clean          # Clean Python cache files
```

## Key Implementation Details

**OAuth Flow:**
- Environment variables: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, `LINKEDIN_REDIRECT_URI`
- Token storage in SQLite database with expiration tracking
- Default user_id: "default_user" (configurable)

**Database Schema:**
- Table: `linkedin_tokens`
- Fields: user_id (PK), access_token, refresh_token, token_type, expires_at, scope, email, created_at, updated_at
- Automatic token expiration validation

**Service Dependencies:**
- `python3-linkedin` library for comprehensive LinkedIn API access
- `authlib` for OAuth2 flows
- `SQLAlchemy` with async SQLite for token persistence
- `FastMCP` for MCP protocol implementation

**LinkedIn API Compliance:**
- Content validation (3000 char limit, 10 mentions max)
- Rate limiting awareness (1 post/minute, 100 posts/day)
- Professional content guidelines enforcement

## MCP Integration

**Available MCP Tools:**
- `start_linkedin_auth` - Generate OAuth URL
- `exchange_linkedin_token` - Exchange auth code for token
- `get_linkedin_profile` - Get profile with posting guidelines
- `create_linkedin_post` - Create posts with validation
- `linkedin_posting_guidelines` - Show posting rules

**Available MCP Resources:**
- `linkedin://guidelines` - Access posting guidelines
- `linkedin://profile/{user_id}` - Access profile data

## Testing the Server

**Local HTTP testing:**
- Visit `http://localhost:8000/docs` for Swagger UI
- OAuth flow: `/linkedin/auth` → LinkedIn → `/linkedin/callback`
- Profile: `GET /linkedin/profile`
- Posts: `POST /linkedin/posts`

**MCP testing:**
```bash
# Test with MCP CLI
npm install -g @modelcontextprotocol/cli
mcp dev main.py --stdio
```

## Common Issues

**OAuth Setup:**
- Ensure LinkedIn app has correct products enabled: "Sign In with LinkedIn using OpenID Connect", "Share on LinkedIn"
- Redirect URI must match exactly: `http://localhost:8000/linkedin/callback`

**Token Management:**
- Tokens automatically expire and are validated before use
- Use `get_valid_token()` to check token validity
- Database auto-initializes on first use

**API Permissions:**
- Many LinkedIn endpoints require specific partnership access
- Connections API is heavily restricted
- Job search requires special permissions
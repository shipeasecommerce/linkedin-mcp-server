# LinkedIn MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to interact with LinkedIn's API through standardized tool calls. Compatible with Claude Code, Claude Desktop, and other MCP-enabled clients.

## Features

- **OAuth Authentication** - Secure LinkedIn OAuth 2.0 flow
- **Profile Management** - Retrieve user profile information
- **Post Creation** - Create and publish LinkedIn posts with validation
- **Content Guidelines** - Built-in LinkedIn posting compliance
- **Token Management** - Automatic token storage and expiration handling
- **Rate Limiting** - Respects LinkedIn's API limits (1 post/minute, 100/day)

## Quick Start

### Prerequisites

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) package manager
- LinkedIn Developer App (see [setup guide](tutorial.md#step-1-linkedin-developer-setup))

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd linkedin-mcp
```

2. Install dependencies:
```bash
npm run install
# or
uv sync
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your LinkedIn app credentials
```

### Usage with Claude Code

Add the MCP server to Claude Code:

```bash
claude mcp add-json linkedin-mcp '{"type":"stdio","command":"uv","args":["--directory", "/path/to/linkedin-mcp", "run", "python", "main.py", "--stdio"]}'
```

### Usage with Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "linkedin-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/linkedin-mcp", "run", "python", "main.py", "--stdio"],
      "env": {
        "LINKEDIN_CLIENT_ID": "your_client_id",
        "LINKEDIN_CLIENT_SECRET": "your_client_secret",
        "LINKEDIN_REDIRECT_URI": "http://localhost:8000/linkedin/callback"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `start_linkedin_auth` | Generate OAuth authorization URL |
| `exchange_linkedin_token` | Exchange auth code for access token |
| `check_linkedin_auth_status` | Verify authentication status |
| `get_linkedin_profile` | Retrieve profile information |
| `create_linkedin_post` | Create and publish posts |
| `linkedin_posting_guidelines` | View content guidelines |

## Development

### Running the Server

```bash
# OAuth callback server (for authentication)
python main.py

# MCP server (for Claude integration)
python main.py --stdio

# With uvicorn (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality

```bash
npm run lint      # Run ruff linting
npm run format    # Format code with ruff
npm run test      # Run pytest tests
npm run clean     # Clean Python cache files
```

### Testing

```bash
# Local HTTP testing
curl http://localhost:8000/docs

# MCP testing
npm install -g @modelcontextprotocol/cli
mcp dev main.py --stdio
```

## Architecture

- **main.py** - FastMCP server with unified MCP tools and OAuth callback
- **linkedin_api.py** - Direct LinkedIn API wrapper using requests
- **database.py** - SQLAlchemy-based token storage with async SQLite

## LinkedIn API Compliance

This server enforces LinkedIn's content policies and technical limitations:

- **Content Validation**: 3000 character limit, 10 mentions maximum
- **Rate Limiting**: 1 post per minute, 100 posts per day
- **Professional Standards**: Content guidelines enforcement
- **Token Management**: Automatic expiration handling

## Troubleshooting

### Common Issues

1. **OAuth Redirect Mismatch**: Ensure redirect URI matches exactly in LinkedIn app settings
2. **Permission Errors**: Verify LinkedIn app has required products enabled
3. **Token Expiration**: Tokens expire after 60 days, re-authenticate when needed
4. **Rate Limits**: LinkedIn allows 1 post per minute, 100 posts per day

### Getting Help

- Check the [Tutorial](tutorial.md) for detailed setup instructions
- Review LinkedIn API [documentation](https://docs.microsoft.com/en-us/linkedin/)
- See [MCP specification](https://spec.modelcontextprotocol.io/) for protocol details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

[MIT License](LICENSE)

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- LinkedIn API integration via [python3-linkedin](https://github.com/DEKHTIARJonathan/python3-linkedin)
- Model Context Protocol by [Anthropic](https://github.com/modelcontextprotocol)
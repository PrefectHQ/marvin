# MCP Server Registry

A decentralized registry for discovering MCP (Machine Capability Protocol) servers via AT Protocol.

## Overview

The MCP Server Registry enables:
1. Discovery of MCP servers via AT Protocol
2. Verification of server ownership through DIDs
3. Real-time status monitoring of available servers

## How It Works

### Server Discovery
MCP servers are discovered through AT Protocol records. Each server record contains:
- Name: Display name of the server
- Package: URL or package identifier for installation
- Type: Record type (app.mcp.server)
- Description: What the server does
- Tools: List of available MCP tools
- Version: Optional version number
- Last Registered: Timestamp of last registration

These records are stored in users' AT Protocol repositories under the `app.mcp.server` collection.

### Authentication & Trust
- Each server record is cryptographically signed by its publisher's DID
- Records can only be modified/deleted by their original publisher
- The registry UI shows who published each server

## Running the Registry

```bash
cd registry
npm install
HANDLE=your.handle PASSWORD=your-password npm run dev
```

The registry will be available at:
- Web UI: http://localhost:3000
- API: http://localhost:3000/api/servers

## Publishing Your MCP Server

To make your MCP server discoverable, use the provided Python script:

```python
from mcp.server.fastmcp import FastMCP
from server import register_mcp_server_with_atproto

mcp = FastMCP("My Server")

@mcp.tool()
def my_tool():
    """My cool tool"""
    return "Hello!"

with register_mcp_server_with_atproto(
    mcp,
    name="My Server",
    package="https://github.com/me/repo/blob/main/server.py",
    description="Does cool stuff"
):
    mcp.run()
```

The script will:
1. Register your server with ATProto if credentials are provided
2. Create a stable record key based on the package URL
3. Update existing records if the server is already registered
4. Track registration timestamps

## Development

The registry consists of:
- `server.py`: MCP server implementation with ATProto registration
- `registry/`: Web UI for browsing servers
  - `src/components/App.tsx`: Main UI components
  - `src/server/api.ts`: API endpoints for server discovery
  - `src/styles/styles.css`: UI styling

## Contributing

This is an experimental project. Feel free to submit issues and pull requests.

## License

MIT

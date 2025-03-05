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
- Server ID: A unique identifier
- Endpoint: WebSocket URL where the server can be reached
- Description: What the server does
- Optional metadata (version, capabilities, etc.)

These records are stored in users' AT Protocol repositories under the `app.mcp.server` collection.

### Authentication & Trust
- Each server record is cryptographically signed by its publisher's DID
- Records can only be modified/deleted by their original publisher
- The registry UI shows who published each server

## Running the Registry

```bash
cd registry
bun install
HANDLE=your.handle PASSWORD=your-password bun dev
```

The registry will be available at:
- Web UI: http://localhost:3000
- API: http://localhost:3000/api/servers
- API with DID: http://localhost:3000/api/servers/{did}

## API Endpoints

### GET /api/servers
List all MCP servers for the authenticated user

### GET /api/servers/{did}
List all MCP servers published by a specific DID

### DELETE /api/servers/{serverId}
Delete a server record (must be authenticated as the publisher)

## Publishing Your MCP Server

To make your MCP server discoverable, publish a record to your AT Protocol repository:

```typescript
agent.api.com.atproto.repo.putRecord({
  repo: yourDID,
  collection: 'app.mcp.server',
  rkey: 'unique-server-id',
  record: {
    serverId: 'unique-server-id',
    endpoint: 'wss://your-server.com',
    description: 'Description of your server capabilities',
    // Optional:
    version: '1.0.0',
    pubKey: 'your-public-key',
    capabilities: ['git', 'slack', etc]
  }
})
```

## Development

The registry consists of:
- `src/index.ts`: Main registry service
- `src/api.ts`: API endpoints for server discovery
- `src/ui.ts`: Web UI for browsing servers
- `src/mcp_server.ts`: AT Protocol lexicon definition

## Future Improvements

1. Search and filtering of servers
2. Server categories and tags
3. Server ratings and reviews
4. Advanced server metadata
5. Integration with MCP client libraries

## Contributing

This is an experimental project. Feel free to submit issues and pull requests.

## License

MIT

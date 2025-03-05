# MCP Server Registry

A decentralized registry for discovering MCP servers via AT Protocol. The registry allows MCP server operators to publish their servers and users to discover available servers.

## Components

This project consists of two parts:

1. **Registry Service** (this repository): A web application that discovers and displays MCP servers published on AT Protocol
2. **MCP Servers**: Individual servers that provide AI tools and services (run separately by server operators)

## Running the Registry

1. Clone this repository:
```bash
git clone <repository-url>
cd registry
```

2. Install dependencies:
```bash
bun install
```

3. Start the registry:
```bash
# Development mode with hot reload
HANDLE=your.bsky.social PASSWORD=your-password bun run dev

# Production mode
HANDLE=your.bsky.social PASSWORD=your-password bun run start
```

The registry will be available at:
- Web UI: http://localhost:3000
- API: http://localhost:3001/api

## Publishing Your MCP Server

To publish your MCP server to the registry:

1. Create a new directory for your server:
```bash
mkdir my-mcp-server
cd my-mcp-server
```

2. Initialize a new project:
```bash
bun init
```

3. Install dependencies:
```bash
bun add @atproto/api express ws
```

4. Create a basic MCP server (example):
```typescript
// src/index.ts
import express from 'express';
import { WebSocketServer } from 'ws';
import { BskyAgent } from '@atproto/api';

const app = express();
const wss = new WebSocketServer({ noServer: true });

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Start server
const server = app.listen(3002, () => {
  console.log('MCP Server running on port 3002');
});

// Handle WebSocket connections
server.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

// Handle WebSocket messages
wss.on('connection', (ws) => {
  ws.on('message', async (message) => {
    const data = JSON.parse(message.toString());
    // Handle MCP commands here
    ws.send(JSON.stringify({ status: 'ok', result: 'Hello from MCP!' }));
  });
});

// Publish server to AT Protocol
async function publishServer() {
  const agent = new BskyAgent({
    service: 'https://bsky.social'
  });

  await agent.login({
    identifier: process.env.HANDLE || '',
    password: process.env.PASSWORD || ''
  });

  await agent.post({
    text: \`MCP Server
Endpoint: ws://localhost:3002
Description: My awesome MCP server
Type: app.mcp.server\`
  });
}

publishServer().catch(console.error);
```

5. Start your MCP server:
```bash
HANDLE=your.bsky.social PASSWORD=your-password bun run src/index.ts
```

Your server will be:
- Running on ws://localhost:3002
- Published to AT Protocol
- Discoverable by the registry

## API Reference

### Registry API

- `GET /api/servers` - List all discovered MCP servers
- `DELETE /api/servers/:serverId` - Delete a server record (must be owner)

### MCP Server API

Required endpoints for MCP servers:
- `GET /api/health` - Health check endpoint
- `WebSocket /` - MCP command interface

## Development

- Frontend: React + Vite
- Backend: Express + AT Protocol
- Development server includes hot reload for both frontend and backend 
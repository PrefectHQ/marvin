try:
    from pydantic_ai.mcp import MCPServer, MCPServerStdio
except ImportError:
    from pydantic_ai.mcp import MCPToolset as MCPServer

    MCPServerStdio = None

__all__ = ["MCPServer", "MCPServerStdio"]

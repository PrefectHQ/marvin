# MCP integration

Agents accept MCP connections through `mcp_servers`. Pydantic AI 2.x uses its native `MCPToolset`; the older integration adapts FastMCP servers for Pydantic AI 1.x.

`MCPManager` owns connection startup and cleanup. A thread context keeps its manager available across orchestrator calls. Agents pass the active connections to Pydantic AI as toolsets.

`discover_mcp_tools` and its wrapper are a legacy manual-discovery path. They are tested separately but are not called by the orchestrator. Do not register the same tools through both paths.

See [the MCP guide](../../../../docs/guides/mcp.mdx) for usage and `tests/basic/engine/test_mcp_toolset.py` for a real in-process connection, tool failure, reuse, and cleanup.

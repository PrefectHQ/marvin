# Experimental: Using MCP Servers with Marvin Agents

**Status:** Experimental

This guide outlines ongoing work to integrate Marvin Agents with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## What is MCP?

The Model Context Protocol is a standard way for AI applications (like agents, coding assistants, etc.) to connect to external tools and services using a common interface. Imagine a world where your Marvin Agent could seamlessly use a specialized code execution tool, a web search service, or a database query tool provided by separate MCP "servers" without needing custom code for each integration.

## Marvin's Goal

While Marvin's underlying AI engine ([Pydantic AI](https://ai.pydantic.dev/)) already supports acting as an MCP client, Marvin aims to provide a more streamlined developer experience.

Our goal is to allow you to simply provide MCP server configurations to a Marvin `Agent`, and have Marvin handle the necessary connections and tool interactions automatically, including integrating these external tools with Marvin's event handling and logging system.

You shouldn't need to manage the MCP server lifecycle (like starting/stopping subprocesses or managing HTTP connections) yourself when using standard Marvin functions like `agent.run_async()`.

This effort originated from community discussion in [GitHub Issue #1122](https://github.com/PrefectHQ/marvin/issues/1122).

## Target Usage

The intended way to use an MCP server with a Marvin Agent is as follows:

1.  **Define your MCP Server:** Configure an instance of an MCP server client provided by `pydantic-ai` (e.g., `MCPServerStdio` for subprocess-based servers or `MCPServerHTTP` for servers running elsewhere).
2.  **Instantiate your Marvin Agent:** Pass the server instance(s) in the `mcp_servers` list during agent creation.
3.  **Run the Agent:** Use the agent as normal (e.g., `agent.run_async(...)`). Marvin's orchestrator should handle starting/stopping the server (for `MCPServerStdio`) and making its tools available to the agent.

```python
# Example: Using the MCP Run Python server (stdio)
# (Requires Deno and server install: see examples/agent_mcp.py)

import asyncio

from pydantic_ai.mcp import MCPServerStdio
from marvin.agents import Agent

# 1. Define the MCP Server configuration
run_python_server = MCPServerStdio(
    command='deno',
    args=[
        'run',
        '-A', # Use -A for simplicity, adjust permissions as needed
        'jsr:@pydantic/mcp-run-python',
        'stdio',
    ]
)

# 2. Instantiate the Marvin Agent
calculator_agent = Agent(
    name="MCP Calculator",
    instructions=(
        "Use available tools to answer the user's question. You have access"
        " to an MCP server that provides a `run_python_code` tool."
    ),
    mcp_servers=[run_python_server],
)

# 3. Run the agent
async def main():
    result = await calculator_agent.run_async(
        "How many days are between 2000-01-01 and 2025-03-18?"
    )
    print("\\nAgent Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

```
*(See `examples/agent_mcp.py` for the full runnable example)*

## Current Status

The basic plumbing for accepting `mcp_servers` in the `Agent` is in place. The server lifecycle (startup/shutdown, especially for `MCPServerStdio`) is now managed correctly within Marvin's `Orchestrator` using a dedicated internal context manager, separating it from the per-turn agent execution logic. This aligns better with the underlying Pydantic AI patterns and resolves previous async conflicts.

Work primarily involved refactoring the `Orchestrator` and ensuring Marvin's event handling (`handle_agentlet_events`) correctly processes Pydantic AI events, including the termination conditions for both `EndTurn` tools and natural language responses.

Ongoing work involves:
*   Ensuring MCP tools (beyond the basic `run_python_code` example) are correctly represented and invoked.
*   Verifying seamless integration of MCP tool calls and results with Marvin's event handlers (e.g., `PrintHandler`, logging handlers).
*   Addressing outstanding type hint issues and potential edge cases.
*   Thorough testing with various MCP server types (e.g., HTTP SSE).

This feature is experimental, and the API or implementation details might change. 
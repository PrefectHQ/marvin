# examples/agent_mcp.py
import asyncio

from pydantic_ai.mcp import MCPServerStdio

from marvin.agents import Agent

# 1. Define the MCP Server configuration
#    Using the MCP Run Python server via stdio as an example
#    (Requires Deno and the server to be installed: `deno install -A -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python`)
run_python_server = MCPServerStdio(
    command="deno",
    args=[
        "run",
        "-A",  # Use -A for simplicity, adjust permissions as needed
        "jsr:@pydantic/mcp-run-python",
        "stdio",
    ],
)

# 2. Instantiate the Marvin Agent, passing the server via `mcp_servers`
calculator_agent = Agent(
    name="MCP Calculator",
    instructions=(
        "Use available tools to answer the user's question. You have access"
        " to an MCP server that provides a `run_python_code` tool."
    ),
    mcp_servers=[run_python_server],
)


# 3. Run the agent - no explicit context manager should be needed by the user
async def main():
    result = await calculator_agent.run_async(
        "How many days are between 2000-01-01 and 2025-03-18?"
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

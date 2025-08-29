import asyncio
import os
from pathlib import Path
from typing import Annotated, TypedDict

from pydantic import Field
from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP
from rich import print as pprint

import marvin


class Reflection(TypedDict):
    score: Annotated[int, Field(ge=0, le=100)]
    areas_for_improvement: list[str]


# GitHub MCP Server over HTTP (hosted by GitHub)
# This connects to GitHub's official MCP server via HTTP
# Note: Requires authentication - you'll need to provide auth headers
# See: https://github.blog/changelog/2025-06-12-remote-github-mcp-server-is-now-available-in-public-preview/
github_server_http = MCPServerStreamableHTTP(
    url="https://api.githubcopilot.com/mcp/",
    # Add authentication headers if you have a token:
    headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
)

# Alternative: Local servers using stdio transport
# Requires Deno: `deno install -A ... jsr:@pydantic/mcp-run-python`
run_python_server = MCPServerStdio(
    command="deno",
    args=["run", "-A", "jsr:@pydantic/mcp-run-python", "stdio"],
)

# Requires uv: `uvx mcp-server-git`
git_server = MCPServerStdio(
    command="uvx",
    args=["mcp-server-git"],
)


def write_summary_of_work(description: str, file_path: str) -> str:
    """log your efforts in your own style"""
    Path(file_path).write_text(description)
    return f"Summary written to {file_path}"


# Agent using HTTP transport (GitHub MCP)
github_agent = marvin.Agent(
    name="GitHubAgent",
    instructions="Use the GitHub MCP server to interact with GitHub repositories, issues, and PRs.",
    mcp_servers=[github_server_http],
)

# Agent using local stdio transport servers
linus = marvin.Agent(
    name="Linus",
    instructions="Use the available tools as needed to accomplish the user's goal.",
    mcp_servers=[run_python_server, git_server],
    tools=[write_summary_of_work],
)


async def main_github():
    """Example using GitHub MCP server over HTTP"""
    pprint("\n--- GitHub MCP Server (HTTP Transport) Example ---")
    with marvin.Thread():
        # Note: You may need to authenticate on first use
        result = await github_agent.run_async(
            "List the most recent issues in the prefecthq/marvin repository"
        )
        pprint("\n--- GitHub Result ---")
        pprint(result)


async def main_local():
    """Example using local MCP servers with stdio transport"""
    pprint("\n--- Local MCP Servers (Stdio Transport) Example ---")
    with marvin.Thread():
        result = await linus.run_async(
            (
                "1. Get the latest commit hash from this repo using the git_log tool\n"
                "2. Report how many characters long the commit hash is\n"
                "3. Calculate the square root of that number with python\n"
                "finish with a haiku about your experience"
            )
        )
        pprint("\n--- Final Result ---")
        pprint(result)

        pprint("\n--- Reflection ---")
        pprint(
            await linus.run_async(
                "reflect on your work and write a short `summary.txt` file",
                result_type=Reflection,
            )
        )

        if Path("summary.txt").exists():
            input("\n--- As expected, summary.txt exists - hit enter to remove it")
            Path("summary.txt").unlink()
        else:
            raise RuntimeError("agent did not write summary.txt")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--github":
        # Run GitHub HTTP example
        asyncio.run(main_github())
    else:
        # Run local stdio example (default)
        asyncio.run(main_local())

    # To run both examples:
    # asyncio.run(main_github())
    # asyncio.run(main_local())

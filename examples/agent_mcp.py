import asyncio
import os
from pathlib import Path

from pydantic_ai.mcp import MCPServerStdio
from rich import print as pprint

from marvin.agents import Agent

# Requires Deno: `deno install -A ... jsr:@pydantic/mcp-run-python`
run_python_server = MCPServerStdio(
    command="deno",
    args=["run", "-A", "jsr:@pydantic/mcp-run-python", "stdio"],
    env=dict(os.environ),
)

# Requires uv: `uvx mcp-server-git`
git_server = MCPServerStdio(
    command="uvx",
    args=["mcp-server-git"],
    env=dict(os.environ),
)


def write_summary_of_work(description: str, file_path: str) -> str:
    """log your efforts"""
    Path(file_path).write_text(description)
    return f"Summary written to {file_path}"


git_agent = Agent(
    name="Git Agent",
    instructions="Use the available tools as needed to accomplish the user's goal.",
    mcp_servers=[run_python_server, git_server],
    tools=[write_summary_of_work],
)


async def main():
    task = (
        "Get the latest commit hash from this repository (path '.') and report how many characters long it is."
        " Finally, report the square root of that number and write a summary of your work to a file called 'summary.txt'"
    )
    pprint(f"--- Running task: ---\n{task}\n" + "-" * 20)

    pprint("\n--- Starting Agent Run ---")
    result = await git_agent.run_async(task)
    pprint("\n--- Final Result ---")
    pprint(result)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from pathlib import Path

from pydantic_ai.mcp import MCPServerStdio
from rich import print as pprint

from marvin.agents import Agent

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


linus = Agent(
    name="Linus",
    instructions="Use the available tools as needed to accomplish the user's goal.",
    mcp_servers=[run_python_server, git_server],
    tools=[write_summary_of_work],
)


async def main():
    task = (
        "Get the latest commit hash from this repo and report how many characters long it is."
        " Then, report the square root of that number and write a 'summary.txt' based on your work."
    )
    pprint(f"--- Running task: ---\n{task}\n" + "-" * 20)
    pprint("\n--- Starting Agent Run ---")
    result = await linus.run_async(task)
    pprint("\n--- Final Result ---")
    pprint(result)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from pathlib import Path
from typing import Annotated, TypedDict

from pydantic import Field
from pydantic_ai.mcp import MCPServerStdio
from rich import print as pprint

import marvin


class Reflection(TypedDict):
    score: Annotated[int, Field(ge=0, le=100)]
    areas_for_improvement: list[str]


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


linus = marvin.Agent(
    name="Linus",
    instructions="Use the available tools as needed to accomplish the user's goal.",
    mcp_servers=[run_python_server, git_server],
    tools=[write_summary_of_work],
)


async def main():
    with marvin.Thread():
        pprint("\n--- Starting Agent Run ---")
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
    asyncio.run(main())

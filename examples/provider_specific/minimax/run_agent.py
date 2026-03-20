"""
» MINIMAX_API_KEY=your-api-key \
uv run examples/provider_specific/minimax/run_agent.py
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin

MINIMAX_API_URL = "https://api.minimax.io/v1"


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set MINIMAX_API_KEY environment variable to your MiniMax API key."
        )
    return OpenAIProvider(api_key=api_key, base_url=MINIMAX_API_URL)


def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    Path(path).write_text(content)


def main() -> None:
    writer = marvin.Agent(
        model=OpenAIModel("MiniMax-M2.7", provider=get_provider()),
        name="MiniMax Writer",
        instructions="Write concise, engaging content for developers",
        tools=[write_file],
    )

    result = marvin.run(
        "how to use pydantic? write haiku to docs.md",
        agents=[writer],
    )
    print(result)


if __name__ == "__main__":
    main()

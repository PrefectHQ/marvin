"""
» AIML_API_KEY=your-api-key \
uv run examples/provider_specific/aimlapi/run_agent.py
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin

AIML_API_URL = "https://api.aimlapi.com/v1"


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        raise RuntimeError("Set AIML_API_KEY environment variable to your AI/ML API key.")
    return OpenAIProvider(api_key=api_key, base_url=AIML_API_URL)


def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    Path(path).write_text(content)


def main() -> None:
    writer = marvin.Agent(
        model=OpenAIModel("gpt-4o", provider=get_provider()),
        name="AI/ML Writer",
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

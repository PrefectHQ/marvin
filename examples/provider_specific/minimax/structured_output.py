"""
» MINIMAX_API_KEY=your-api-key \
uv run examples/provider_specific/minimax/structured_output.py
"""

from __future__ import annotations

import os

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing_extensions import TypedDict

import marvin

MINIMAX_API_URL = "https://api.minimax.io/v1"


class LearningResource(TypedDict):
    title: str
    url: str
    summary: str


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set MINIMAX_API_KEY environment variable to your MiniMax API key."
        )
    return OpenAIProvider(api_key=api_key, base_url=MINIMAX_API_URL)


def main() -> None:
    researcher = marvin.Agent(
        model=OpenAIModel("MiniMax-M2.7", provider=get_provider()),
        name="Resource Researcher",
        instructions=(
            "Return structured JSON describing useful developer resources."
        ),
    )

    resources = marvin.run(
        "share three quickstart resources for building AI applications with Python",
        result_type=list[LearningResource],
        agents=[researcher],
    )

    for resource in resources:
        print(f"- {resource['title']}\n  {resource['url']}\n  {resource['summary']}\n")


if __name__ == "__main__":
    main()

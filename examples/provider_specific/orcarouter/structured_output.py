"""
» ORCAROUTER_API_KEY=your-api-key \
uv run examples/provider_specific/orcarouter/structured_output.py
"""

from __future__ import annotations

import os

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing_extensions import TypedDict

import marvin

ORCAROUTER_API_URL = "https://api.orcarouter.ai/v1"


class LearningResource(TypedDict):
    title: str
    url: str
    summary: str


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("ORCAROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set ORCAROUTER_API_KEY environment variable to your OrcaRouter API key."
        )
    return OpenAIProvider(api_key=api_key, base_url=ORCAROUTER_API_URL)


def main() -> None:
    researcher = marvin.Agent(
        model=OpenAIModel("openai/gpt-5", provider=get_provider()),
        name="Resource Researcher",
        instructions=(
            "Return structured JSON describing useful developer resources for OrcaRouter."
        ),
    )

    resources = marvin.run(
        "share three quickstart resources for building with OrcaRouter",
        result_type=list[LearningResource],
        agents=[researcher],
    )

    for resource in resources:
        print(f"- {resource['title']}\n  {resource['url']}\n  {resource['summary']}\n")


if __name__ == "__main__":
    main()

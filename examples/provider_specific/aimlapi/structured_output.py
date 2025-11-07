"""
» AIML_API_KEY=your-api-key \
uv run examples/provider_specific/aimlapi/structured_output.py
"""

from __future__ import annotations

import os
from typing_extensions import TypedDict

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin

AIML_API_URL = "https://api.aimlapi.com/v1"


class LearningResource(TypedDict):
    title: str
    url: str
    summary: str


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("AIML_API_KEY")
    if not api_key:
        raise RuntimeError("Set AIML_API_KEY environment variable to your AI/ML API key.")
    return OpenAIProvider(api_key=api_key, base_url=AIML_API_URL)


def main() -> None:
    researcher = marvin.Agent(
        model=OpenAIModel("gpt-4o", provider=get_provider()),
        name="Resource Researcher",
        instructions=(
            "Return structured JSON describing useful developer resources for the AI/ML API."
        ),
    )

    resources = marvin.run(
        "share three quickstart resources for building with the AI/ML API",
        result_type=list[LearningResource],
        agents=[researcher],
    )

    for resource in resources:
        print(f"- {resource['title']}\n  {resource['url']}\n  {resource['summary']}\n")


if __name__ == "__main__":
    main()

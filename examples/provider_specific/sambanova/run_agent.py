"""
SambaNova provider example for Marvin.

» SAMBANOVA_API_KEY=your-api-key \
uv run examples/provider_specific/sambanova/run_agent.py
"""

from __future__ import annotations

import os

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin

SAMBANOVA_API_URL = "https://api.sambanova.ai/v1"


def get_provider() -> OpenAIProvider:
    api_key = os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set SAMBANOVA_API_KEY environment variable to your SambaNova API key."
        )
    return OpenAIProvider(api_key=api_key, base_url=SAMBANOVA_API_URL)


def main() -> None:
    samba_agent = marvin.Agent(
        model=OpenAIModel("Meta-Llama-3.3-70B-Instruct", provider=get_provider()),
        name="SambaNova Assistant",
        instructions="You are a helpful coding assistant powered by SambaNova.",
    )

    result = marvin.run(
        "Explain what a trie data structure is in 2 sentences.",
        agents=[samba_agent],
    )
    print(result)


if __name__ == "__main__":
    main()
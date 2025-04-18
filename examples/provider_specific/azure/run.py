"""
» OPENAI_API_VERSION=2024-12-01-preview \
AZURE_OPENAI_ENDPOINT=https://<your-endpoint>.openai.azure.com/ \
AZURE_OPENAI_API_KEY=<your-api-key> \
uv run examples/provider_specific/azure/run.py
"""

from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin

if __name__ == "__main__":
    azure_agent = marvin.Agent(
        model=OpenAIModel(
            model_name="gpt-4o",
            provider=OpenAIProvider(openai_client=AsyncAzureOpenAI()),
        ),
    )

    marvin.run(
        "what is the capital of the moon?",
        agents=[azure_agent],
    )

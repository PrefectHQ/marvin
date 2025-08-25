import os
from pathlib import Path

from pydantic_ai.models.openai import OpenAIModel

import marvin
from marvin.providers.aimlapi import AIMLAPIProvider


def write_file(path: str, content: str) -> None:
    """Write content to a file."""
    Path(path).write_text(content)


writer = marvin.Agent(
    model=OpenAIModel(
        "gpt-4o-mini",
        provider=AIMLAPIProvider(api_key=os.getenv("AIML_API_KEY")),
    ),
    name="AI/ML Writer",
    instructions="Write concise, engaging content for developers",
    tools=[write_file],
)

async def main():
    result = await marvin.run("how to use pydantic? write haiku to docs.md", agents=[writer])
    print(result)

if __name__ == "__main__":
    asyncio.run(main())

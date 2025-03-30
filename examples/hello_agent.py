import os
from pathlib import Path

import httpx
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import marvin


def write_file(path: str, content: str):
    """Write content to a file"""
    _path = Path(path)
    _path.write_text(content)


writer = marvin.Agent(
    model=OpenAIModel(
        "gpt-4o",
        provider=OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY", "gonna fail"),
            base_url="https://api.openai.com/v1",
            http_client=httpx.AsyncClient(
                # proxy="http://localhost:8080",
                # headers={"x-SOME-HEADER": "some-value"},
            ),
        ),
    ),
    name="Technical Writer",
    instructions="Write concise, engaging content for developers",
    tools=[write_file],
)

result = marvin.run("how to use pydantic? write to docs.md", agents=[writer])
print(result)

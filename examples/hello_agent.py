import os
from pathlib import Path

import httpx
from pydantic_ai.models.anthropic import AnthropicModel

import marvin


def write_file(path: str, content: str):
    """Write content to a file"""
    _path = Path(path)
    _path.write_text(content)


writer = marvin.Agent(
    model=AnthropicModel(
        "anthropic/claude-3-5-sonnet@latest",
        http_client=httpx.AsyncClient(
            timeout=10,
            # proxy="http://localhost:8080",
            headers={"x-api-key": os.getenv("ANTHROPIC_API_KEY", "gonna fail")},
        ),
    ),
    name="Technical Writer",
    instructions="Write concise, engaging content for developers",
    tools=[write_file],
)

result = marvin.run("how to use pydantic? write haiku to docs.md", agents=[writer])

print(result)

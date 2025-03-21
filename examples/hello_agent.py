import os
from pathlib import Path

from pydantic_ai.models.anthropic import AnthropicModel

import marvin


def write_file(path: str, content: str):
    """Write content to a file"""
    _path = Path(path)
    _path.write_text(content)


writer = marvin.Agent(
    model=AnthropicModel(
        model_name="claude-3-5-sonnet-latest",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    name="Technical Writer",
    instructions="Write concise, engaging content for developers",
    tools=[write_file],
)

result = marvin.run("how to use pydantic? write to docs.md", agents=[writer])
print(result)

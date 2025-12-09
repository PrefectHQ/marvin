# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "agentic-learning",
#     "pydantic-ai",
#     "pydantic-settings",
# ]
# [tool.uv]
# prerelease = "allow"
# ///
"""
agentic learning SDK demo

this example shows how to use the agentic-learning SDK with pydantic-ai.
the SDK automatically captures conversations and manages persistent memory.

prerequisites:
    LETTA_API_KEY and ANTHROPIC_API_KEY in .env

usage:
    uv run examples/agentic_learning_demo.py
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    letta_api_key: str


settings = Settings()
os.environ["LETTA_API_KEY"] = settings.letta_api_key
os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

from agentic_learning import learning  # noqa: E402
from pydantic_ai import Agent  # noqa: E402

agent = Agent("anthropic:claude-sonnet-4-20250514")


def ask(message: str):
    print(f"user: {message}\n")

    with learning(agent="pydantic-ai-demo"):
        result = agent.run_sync(message)
        print(f"assistant: {result.output}\n")


if __name__ == "__main__":
    while True:
        message = input("you: ")
        if message.lower() in ("quit", "exit", "q"):
            break
        ask(message)

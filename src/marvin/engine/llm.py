"""Utility functions for LLM completions using Pydantic AI."""

from typing import TYPE_CHECKING

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from typing_extensions import TypeVar

if TYPE_CHECKING:
    pass


PydanticAIMessage = ModelRequest | ModelResponse


def SystemMessage(content: str) -> ModelRequest:
    return ModelRequest(parts=[SystemPromptPart(content=content)])


def UserMessage(content: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=content)])


def AgentMessage(content: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=content)])


# Type variable for generic response types
T = TypeVar("T")

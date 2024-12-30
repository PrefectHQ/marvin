"""
Utility functions for LLM completions using Pydantic AI.
"""

from typing_extensions import TypeVar
import pydantic_ai
from typing import (
    Callable,
    List,
    Optional,
    Type,
    get_type_hints,
)
from pydantic_ai import RunContext
from pydantic_ai.result import RunResult
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    UserPromptPart,
    TextPart,
)
import marvin

# Define Message type union
Message = ModelRequest | ModelResponse


def SystemMessage(content: str) -> ModelRequest:
    return ModelRequest(parts=[SystemPromptPart(content=content)])


def UserMessage(content: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=content)])


def AgentMessage(content: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=content)])


# Type variable for generic response types
T = TypeVar("T")


def bind_tool(agent: pydantic_ai.Agent, func: Callable) -> None:
    """Bind a function as a tool to an agent.

    Inspects the function signature to see if it accepts a RunContext parameter.
    If it does, uses agent.tool(), otherwise uses agent.tool_plain().

    Args:
        agent: The Pydantic AI agent to bind the tool to
        func: The function to bind as a tool
    """
    # Get type hints including RunContext if present
    type_hints = get_type_hints(func)

    # Check if any parameter is annotated as RunContext
    has_run_context = any(hint == RunContext for hint in type_hints.values())

    # Use the appropriate method
    if has_run_context:
        agent.tool()(func)
    else:
        agent.tool_plain()(func)


def create_agentlet(
    model: str,
    result_type: Type[T],
    system_prompt: Optional[
        str | Callable[[], str] | Callable[[RunContext], str]
    ] = None,
    tools: Optional[List[Callable]] = None,
) -> pydantic_ai.Agent:
    kwargs = {}
    if tools:
        kwargs["tools"] = tools
    if system_prompt and isinstance(system_prompt, str):
        kwargs["system_prompt"] = system_prompt

    agentlet = pydantic_ai.Agent(
        model=model,
        result_type=result_type,
        retries=marvin.settings.agent_retries,
        **kwargs,
    )

    # dynamic system prompt
    if system_prompt and isinstance(system_prompt, Callable):
        agentlet.system_prompt(system_prompt)

    return agentlet


async def generate_response(
    agentlet: pydantic_ai.Agent,
    messages: List[Message] = None,
    user_prompt: Optional[str] = None,
) -> RunResult:
    user_prompt = user_prompt or ""
    return await agentlet.run(user_prompt=user_prompt, message_history=messages)

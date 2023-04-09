import asyncio
import inspect
from datetime import datetime
from typing import Any, Callable, Tuple, Union

from langchain.callbacks.base import BaseCallbackHandler, CallbackManager
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    AgentAction,
    AgentFinish,
    AIMessage,
    HumanMessage,
    LLMResult,
    SystemMessage,
)

import marvin
from marvin.models.threads import Message
from marvin.utilities.strings import count_tokens


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for streaming responses.
    """

    def __init__(self, buffer: list[str] = None, on_token_callback: Callable = None):
        """
        Args:
            - buffer: The buffer to store the tokens in. Will be created if not
              provided.
            - on_token_callback: A callback to run on each new token. It will be
              called with the entire buffer as an argument; the last token can
              be accessed with buffer[-1].
        """
        if buffer is None:
            buffer = []
        self.buffer = buffer
        self.on_token_callback = on_token_callback
        super().__init__()

    @property
    def always_verbose(self) -> bool:
        return True

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.buffer.clear()

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        self.buffer.append(token)
        if self.on_token_callback is not None:
            output = self.on_token_callback(self.buffer)
            if inspect.iscoroutine(output):
                asyncio.run(self.on_token_callback(self.buffer))

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Run when LLM ends running."""

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when LLM errors."""

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> Any:
        """Run when chain starts running."""

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> Any:
        """Run when chain ends running."""

    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when chain errors."""

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Run when tool starts running."""

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Run when tool ends running."""

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Run when tool errors."""

    def on_text(self, text: str, **kwargs: Any) -> Any:
        """Run on arbitrary text."""

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run on agent action."""

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """Run on agent end."""


def get_llm(
    model_name: str = None,
    temperature: float = None,
    openai_api_key: str = None,
    on_token_callback: Callable = None,
) -> ChatOpenAI:
    kwargs = dict()
    if on_token_callback is not None:
        kwargs.update(
            streaming=True,
            callback_manager=CallbackManager(
                [StreamingCallbackHandler(on_token_callback=on_token_callback)]
            ),
        )
    return ChatOpenAI(
        model_name=model_name or marvin.settings.openai_model_name,
        temperature=temperature or marvin.settings.openai_model_temperature,
        openai_api_key=(
            openai_api_key or marvin.settings.openai_api_key.get_secret_value()
        ),
        max_tokens=marvin.settings.openai_model_max_tokens,
        **kwargs,
    )


def prepare_messages(
    messages: list[Message],
    context_window_tokens: int = 4096,
) -> Union[AIMessage, HumanMessage, SystemMessage]:
    """Prepare messages for LLM."""

    if sum(count_tokens(msg.content) for msg in messages) >= context_window_tokens:
        messages = trim_to_context_window(messages)

    langchain_messages = []
    for msg in messages:
        if msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "bot":
            langchain_messages.append(AIMessage(content=msg.content))
        elif msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        else:
            raise ValueError(f"Unrecognized role: {msg.role}")
    return langchain_messages


def message_sort_key(
    msg: Message, messages: list[Message]
) -> Tuple[bool, bool, datetime]:
    index = messages.index(msg)
    # prioritize system messages
    is_system = msg.role == "system"
    # then, prefer ai messages preceeded by user messages
    is_ai_after_user = (
        index > 0 and messages[index - 1].role == "user" and msg.role == "ai"
    )
    # then, sort by timestamp
    return (not is_system, not is_ai_after_user, msg.timestamp)


def trim_to_context_window(
    messages: list[Message], max_tokens: int = 4096, first_n: int = 1, last_n: int = 1
):
    processed_messages = []
    token_count = 0

    # Include first and last N messages (if they fit)
    for index, msg in enumerate(messages):
        tokens_needed = count_tokens(msg.content)

        # Check if the message is among the first N messages or the last N messages
        if index < first_n or index >= len(messages) - last_n:
            if token_count + tokens_needed <= max_tokens:
                token_count += tokens_needed
                processed_messages.append(msg)

    # Prepare messages to rank and exclude ones already in processed_messages
    remaining_messages = [
        msg for msg in messages[first_n:-last_n] if msg not in processed_messages
    ]

    # Sort the remaining_messages by heuristics baked into message_sort_key
    remaining_messages.sort(key=lambda x: message_sort_key(x, messages), reverse=True)

    # Include top ranked messages until they can no longer fit
    for msg in remaining_messages:
        tokens_needed = count_tokens(msg.content)
        if token_count + tokens_needed <= max_tokens:
            token_count += tokens_needed
            processed_messages.append(msg)

    # Sort the processed_messages by timestamp to maintain chronological order
    processed_messages.sort(key=lambda x: x.timestamp.timestamp())

    return processed_messages

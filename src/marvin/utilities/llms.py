import asyncio
import inspect
from typing import Any, Callable, Union

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
) -> Union[AIMessage, HumanMessage, SystemMessage]:
    """Prepare messages for LLM."""
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

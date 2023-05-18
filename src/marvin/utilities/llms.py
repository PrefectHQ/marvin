import inspect
from typing import Any, Callable, Union

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

import marvin
from marvin.models.threads import Message


class StreamingCallbackHandler(AsyncCallbackHandler):
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

    async def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.buffer.clear()

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        self.buffer.append(token)
        if self.on_token_callback is not None:
            output = self.on_token_callback(self.buffer)
            if inspect.iscoroutine(output):
                await output


def get_llm(
    model_name: str = None,
    temperature: float = None,
    openai_api_key: str = None,
    on_token_callback: Callable = None,
    request_timeout: int = None,
) -> ChatOpenAI:
    kwargs = dict()
    if on_token_callback is not None:
        kwargs.update(
            streaming=True,
            callbacks=[StreamingCallbackHandler(on_token_callback=on_token_callback)],
        )
    if model_name is None:
        model_name = marvin.settings.openai_model_name
    if temperature is None:
        temperature = marvin.settings.openai_model_temperature
    if request_timeout is None:
        request_timeout = marvin.settings.llm_timeout
    return ChatOpenAI(
        model_name=model_name,
        temperature=temperature,
        openai_api_key=(
            openai_api_key or marvin.settings.openai_api_key.get_secret_value()
        ),
        max_tokens=marvin.settings.openai_model_max_tokens,
        request_timeout=request_timeout,
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

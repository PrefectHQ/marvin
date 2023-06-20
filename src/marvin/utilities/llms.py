import inspect
from logging import Logger
from typing import Any, Callable, Union

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import AIMessage, FunctionMessage, HumanMessage, SystemMessage

import marvin
from marvin.config import LLMBackend, infer_llm_backend
from marvin.models.threads import Message
from marvin.utilities.logging import get_logger


class AsyncStreamingCallbackHandler(AsyncCallbackHandler):
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


def get_model(
    backend: str = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    llm_kwargs: dict[str, Any] = None,
    on_token_callback: Callable = None,
):
    """
    Given a backend, model name, and optional kwargs, returns a callable that
    returns an AI model.
    """

    # override settings with provided kwargs
    _llm_kwargs = marvin.settings.llm_extra_kwargs.copy()
    _llm_kwargs.update(llm_kwargs or {})
    llm_kwargs = _llm_kwargs

    if on_token_callback is not None:
        llm_kwargs.update(
            streaming=True,
            callbacks=[
                AsyncStreamingCallbackHandler(on_token_callback=on_token_callback)
            ],
        )

    if model is None:
        model = marvin.settings.llm_model
    if temperature is None:
        temperature = marvin.settings.llm_temperature
    if max_tokens is None:
        max_tokens = marvin.settings.llm_max_tokens

    if backend is None:
        try:
            backend = infer_llm_backend(model)
        except ValueError:
            backend = marvin.settings.llm_backend

    # OpenAI chat models
    if backend == LLMBackend.OpenAIChat:
        from langchain.chat_models import ChatOpenAI

        return ChatOpenAI(
            openai_api_key=marvin.settings.openai_api_key.get_secret_value(),
            model_name=model,
            max_tokens=max_tokens,
            temperature=temperature,
            openai_api_base=marvin.settings.openai_api_base,
            openai_organization=marvin.settings.openai_organization,
            request_timeout=marvin.settings.llm_request_timeout_seconds,
            **llm_kwargs,
        )

    # AzureChatOpenAI chat models
    elif backend == LLMBackend.AzureOpenAIChat:
        from langchain.chat_models import AzureChatOpenAI

        return AzureChatOpenAI(
            openai_api_key=marvin.settings.openai_api_key.get_secret_value(),
            model_name=model,
            max_tokens=max_tokens,
            temperature=temperature,
            openai_api_base=marvin.settings.openai_api_base,
            openai_organization=marvin.settings.openai_organization,
            request_timeout=marvin.settings.llm_request_timeout_seconds,
            **llm_kwargs,
        )

    # OpenAI completion models
    elif backend == LLMBackend.OpenAI:
        from langchain.llms import OpenAI

        return OpenAI(
            openai_api_key=marvin.settings.openai_api_key.get_secret_value(),
            model_name=model,
            max_tokens=max_tokens,
            temperature=temperature,
            openai_api_base=marvin.settings.openai_api_base,
            openai_organization=marvin.settings.openai_organization,
            request_timeout=marvin.settings.llm_request_timeout_seconds,
            **llm_kwargs,
        )

    # AzureOpenAI completion models
    elif backend == LLMBackend.AzureOpenAI:
        from langchain.llms import AzureOpenAI

        return AzureOpenAI(
            openai_api_key=marvin.settings.openai_api_key.get_secret_value(),
            model_name=model,
            max_tokens=max_tokens,
            temperature=temperature,
            openai_api_base=marvin.settings.openai_api_base,
            openai_organization=marvin.settings.openai_organization,
            request_timeout=marvin.settings.llm_request_timeout_seconds,
            **llm_kwargs,
        )

    # Anthropic chat models
    elif backend == LLMBackend.Anthropic:
        from langchain.chat_models import ChatAnthropic

        return ChatAnthropic(
            anthropic_api_key=marvin.settings.anthropic_api_key.get_secret_value(),
            model=model,
            max_tokens_to_sample=max_tokens,
            temperature=temperature,
            default_request_timeout=marvin.settings.llm_request_timeout_seconds,
            **llm_kwargs,
        )

    # HuggingFaceHub models
    elif backend == LLMBackend.HuggingFaceHub:
        from langchain.llms import HuggingFaceHub

        return HuggingFaceHub(
            huggingfacehub_api_token=marvin.settings.huggingfacehub_api_token.get_secret_value(),
            repo_id=model,
            model_kwargs=llm_kwargs,
        )

    else:
        raise ValueError(f"Unknown LLM backend: {backend}")


def prepare_messages(
    messages: list[Message],
) -> list[Union[AIMessage, HumanMessage, SystemMessage, FunctionMessage]]:
    """Prepare messages for LLM."""
    langchain_messages = []
    for msg in messages:
        if msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content or ""))
        elif msg.role == "ai":
            langchain_messages.append(AIMessage(content=msg.content or ""))
        elif msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content or ""))
        elif msg.role == "function":
            langchain_messages.append(
                FunctionMessage(name=msg.name, content=msg.content or "")
            )
        else:
            raise ValueError(f"Unrecognized role: {msg.role}")
    return langchain_messages


async def call_llm(llm, text: str, logger: Logger = None, **kwargs) -> str:
    """
    Get an LLM response to a string prompt via langchain
    """
    if logger is None:
        logger = get_logger("llm")

    if marvin.settings.verbose:
        logger.debug_kv("Sending text to LLM", text, key_style="green")

    try:
        response = await llm.apredict(text=text, **kwargs)
    # some LLMs, like HuggingFaceHub, don't support async
    except NotImplementedError as exc:
        if "Async generation not implemented for this LLM" in str(exc):
            response = llm.predict(text=text, **kwargs)
        else:
            raise

    return response


async def call_llm_messages(
    llm, messages: list[Message], logger: Logger = None, **kwargs
) -> AIMessage:
    """
    Get an LLM response to a history of Marvin messages via langchain
    """

    if logger is None:
        logger = get_logger("llm")

    langchain_messages = marvin.utilities.llms.prepare_messages(messages)

    if marvin.settings.verbose:
        messages_repr = "\n".join(repr(m) for m in langchain_messages)
        logger.debug_kv("Sending messages to LLM", messages_repr, key_style="green")

    try:
        response = await llm.apredict_messages(messages=langchain_messages, **kwargs)
    # some LLMs, like HuggingFaceHub, don't support async
    except NotImplementedError as exc:
        if "Async generation not implemented for this LLM" in str(exc):
            response: AIMessage = llm.predict_messages(
                messages=langchain_messages, **kwargs
            )
        else:
            raise

    return response

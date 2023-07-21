import abc
import json
from logging import Logger
from typing import Any, Callable, Union

import tiktoken
from pydantic import Field, validator

import marvin
import marvin.utilities.types
from marvin.utilities.messages import Message
from marvin.utilities.types import MarvinBaseModel


class StreamHandler(MarvinBaseModel, abc.ABC):
    callback: Callable[[Message], None] = None

    @abc.abstractmethod
    def handle_streaming_response(self, api_response) -> Message:
        raise NotImplementedError()


class OpenAIFunction(MarvinBaseModel):
    name: str
    description: str = None
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    fn: Callable = Field(None, exclude=True)
    args: dict = None
    """
    Base class for representing a function that can be called by an LLM. The
    format is identical to OpenAI's Functions API.

    Args:
        name (str): The name of the function. description (str): The description
        of the function. parameters (dict): The parameters of the function. fn
        (Callable): The function to be called. args (dict): The arguments to be
        passed to the function.
    """

    @classmethod
    def from_function(cls, fn: Callable, **kwargs):
        return cls(
            name=kwargs.get("name", fn.__name__),
            description=kwargs.get("description", fn.__doc__ or ""),
            parameters=marvin.utilities.types.function_to_schema(fn),
            fn=fn,
        )

    async def query(self, q: str, model: "ChatLLM" = None):
        if not model:
            model = chat_llm()
        self.args = json.loads(
            (
                await model.run(
                    messages=[Message(role="USER", content=q)],
                    functions=[self],
                    function_call={"name": self.name},
                )
            )
            .data.get("function_call")
            .get("arguments")
        )
        return self


class ChatLLM(MarvinBaseModel, abc.ABC):
    name: str = None
    model: str
    max_tokens: int = Field(default_factory=lambda: marvin.settings.llm_max_tokens)
    temperature: float = Field(default_factory=lambda: marvin.settings.llm_temperature)

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    @property
    def context_size(self) -> int:
        return 4096

    def get_tokens(self, text: str, **kwargs) -> list[int]:
        try:
            enc = tiktoken.encoding_for_model(self.model)
        # fallback to the gpt-3.5-turbo tokenizer if the model is not found
        # note this will give the wrong answer for non-OpenAI models
        except KeyError:
            enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return enc.encode(text)

    async def __call__(self, messages, *args, **kwargs):
        return await self.run(messages, *args, **kwargs)

    @abc.abstractmethod
    def format_messages(
        self, messages: list[Message]
    ) -> Union[str, dict, list[Union[str, dict]]]:
        """Format Marvin message objects into a prompt compatible with the LLM model"""
        return messages

    @abc.abstractmethod
    async def run(
        self,
        messages: list[Message],
        functions: list[OpenAIFunction] = None,
        *,
        logger: Logger = None,
        stream_handler: Callable[[Message], None] = False,
        **kwargs,
    ) -> Message:
        """Run the LLM model on a list of messages and optional list of functions"""
        raise NotImplementedError()


def chat_llm(model: str = None, **kwargs) -> ChatLLM:
    """Dispatches to all supported LLM providers"""
    if model is None:
        model = marvin.settings.llm_model

    # automatically detect gpt-3.5 and gpt-4 for backwards compatibility
    if model.startswith("gpt-3.5-turbo") or model.startswith("gpt-4"):
        model = f"openai/{model}"

    # extract the provider and model name
    provider, model_name = model.split("/", 1)

    if provider == "openai":
        from .openai import OpenAIChatLLM

        return OpenAIChatLLM(model=model_name, **kwargs)
    elif provider == "anthropic":
        from .anthropic import AnthropicChatLLM

        return AnthropicChatLLM(model=model_name, **kwargs)
    elif provider == "azure_openai":
        from .azure_openai import AzureOpenAIChatLLM

        return AzureOpenAIChatLLM(model=model_name, **kwargs)
    else:
        raise ValueError(f"Unknown provider/model: {model}")

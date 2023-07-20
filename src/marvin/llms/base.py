import abc
import ast
import inspect
import json
from logging import Logger
from typing import Any, Callable, Union

import tiktoken
from pydantic import Field, validator

import marvin
import marvin.utilities.types
from marvin.utilities.messages import Message, Role
from marvin.utilities.types import LoggerMixin, MarvinBaseModel


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


class ChatLLM(LoggerMixin, MarvinBaseModel, abc.ABC):
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

    async def process_function_call(
        self, message: Message, functions: list[OpenAIFunction]
    ) -> Message:
        """
        Given a message from the LLM that has role FUNCTION_REQUEST, processes
        the function call and returns the message as a FUNCTION_RESPONSE
        message.
        """

        if message.role != Role.FUNCTION_REQUEST:
            return message

        response_data = {}

        function_call = message.data["function_call"]
        fn_name = function_call.get("name")
        fn_args = function_call.get("arguments")
        response_data["name"] = fn_name
        try:
            try:
                fn_args = json.loads(function_call.get("arguments", "{}"))
            except json.JSONDecodeError:
                fn_args = ast.literal_eval(function_call.get("arguments", "{}"))
            response_data["arguments"] = fn_args

            # retrieve the named function
            openai_fn = next((f for f in functions if f.name == fn_name), None)
            if openai_fn is None:
                raise ValueError(f'Function "{function_call["name"]}" not found.')

            if not isinstance(fn_args, dict):
                raise ValueError(
                    "Expected a dictionary of arguments, got a"
                    f" {type(fn_args).__name__}."
                )

            # call the function
            if openai_fn.fn is not None:
                self.logger.debug(
                    f"Running function '{openai_fn.name}' with payload {fn_args}"
                )
                fn_result = openai_fn.fn(**fn_args)
                if inspect.isawaitable(fn_result):
                    fn_result = await fn_result

            # if the function is undefined, return the arguments as its output
            else:
                fn_result = fn_args
            self.logger.debug(f"Result of function '{openai_fn.name}': {fn_result}")
            response_data["is_error"] = False

        except Exception as exc:
            fn_result = (
                f"The function '{fn_name}' encountered an error:"
                f" {str(exc)}\n\nThe payload you provided was: {fn_args}\n\nYou"
                " can try to fix the error and call the function again."
            )
            self.logger.debug_kv("Error", fn_result, key_style="red")
            response_data["is_error"] = True

        response_data["result"] = fn_result

        return Message(
            role=Role.FUNCTION_RESPONSE,
            name=fn_name,
            content=str(fn_result),
            data=response_data,
            llm_response=message.llm_response,
        )


def chat_llm(model: str = None, **kwargs) -> ChatLLM:
    if model is None:
        model = marvin.settings.llm_model

    # automatically detect well-known model providers
    if model.startswith("gpt-3.5-turbo") or model.startswith("gpt-4"):
        model = f"openai/{model}"
    elif model.startswith("claude-"):
        model = f"anthropic/{model}"

    # extract the provider and model name
    provider, model_name = model.split("/", 1)

    if provider == "openai":
        from .providers.openai import OpenAIChatLLM

        return OpenAIChatLLM(model=model_name, **kwargs)
    elif provider == "anthropic":
        from .providers.anthropic import AnthropicChatLLM

        return AnthropicChatLLM(model=model_name, **kwargs)
    elif provider == "azure_openai":
        from .providers.azure_openai import AzureOpenAIChatLLM

        return AzureOpenAIChatLLM(model=model_name, **kwargs)
    else:
        raise ValueError(f"Unknown provider/model: {model}")

import inspect
import json
from logging import Logger
from typing import Any, Callable, Optional, Union

import openai
import openai.openai_object
import tiktoken
from pydantic import Field, validator

import marvin
import marvin.utilities.types
from marvin.models.messages import Message
from marvin.utilities.async_utils import create_task
from marvin.utilities.logging import get_logger
from marvin.utilities.types import MarvinBaseModel

CONTEXT_SIZES = {
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-0613": 4096,
    "gpt-3.5-turbo-16k": 16384,
    "gpt-3.5-turbo-16k-0613": 16384,
    "gpt-4": 8192,
    "gpt-4-0613": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-32k-0613": 32768,
}


class OpenAIFunction(MarvinBaseModel):
    name: str
    description: str = None
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    fn: Callable = Field(None, exclude=True)
    args: Optional[dict] = None
    """
    Base class for representing a function that can be called by the OpenAI API.

    Args:
        name (str): The name of the function.
        description (str): The description of the function.
        parameters (dict): The parameters of the function.
        fn (Callable): The function to be called.
        args (dict): The arguments to be passed to the function.
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
            model = ChatLLM()
        self.args = json.loads(
            (
                await ChatLLM().run(
                    messages=[Message(role="USER", content=q)],
                    functions=[self],
                    function_call={"name": self.name},
                )
            )
            .data.get("function_call")
            .get("arguments")
        )
        return self


class StreamHandler(MarvinBaseModel):
    callback: Callable[[Message], None] = None

    async def handle_streaming_response(
        self,
        openai_response: openai.openai_object.OpenAIObject,
    ) -> Message:
        """
        Accumulate chunk deltas into a full response. Returns the full message.
        Passes partial messages to the callback, if provided.
        """
        response = {"role": None, "content": "", "data": {}}

        async for r in openai_response:
            delta = r.choices[0].delta

            # streaming deltas are stored in the 'data' field during streaming
            response["data"]["streaming_delta"] = delta.to_dict_recursive()

            if "role" in delta:
                response["role"] = delta.role

            if fn_call := delta.get("function_call"):
                if "function_call" not in response["data"]:
                    response["data"]["function_call"] = {"name": None, "arguments": ""}
                if "name" in fn_call:
                    response["data"]["function_call"]["name"] = fn_call.name
                if "arguments" in fn_call:
                    response["data"]["function_call"]["arguments"] += (
                        fn_call.arguments or ""
                    )

            if "content" in delta:
                response["content"] += delta.content or ""

            if self.callback:
                callback_result = self.callback(Message(**response))
                if inspect.isawaitable(callback_result):
                    create_task(callback_result(Message(**response)))

        # remove the streaming delta from the response data
        response["data"].pop("streaming_delta", None)
        return Message(**response)


class ChatLLM(MarvinBaseModel):
    name: str = None
    model: str = Field(default_factory=lambda: marvin.settings.llm_model)
    max_tokens: int = Field(default_factory=lambda: marvin.settings.llm_max_tokens)
    temperature: float = Field(default_factory=lambda: marvin.settings.llm_temperature)

    _tokenizer: Optional[Callable] = None

    @validator("name", always=True)
    def default_name(cls, v):
        if v is None:
            v = cls.__name__
        return v

    @property
    def context_size(self) -> int:
        return CONTEXT_SIZES.get(self.model, 4096)

    def get_tokens(self, text: str, **kwargs) -> list[int]:
        enc = tiktoken.encoding_for_model(self.model)
        return enc.encode(text)

    async def __call__(self, messages, *args, **kwargs):
        return await self.run(messages, *args, **kwargs)

    async def run(
        self,
        messages: list[Message],
        *,
        functions: list[OpenAIFunction] = None,
        function_call: Union[str, dict[str, str]] = None,
        logger: Logger = None,
        stream_handler: Callable[[Message], None] = False,
        **kwargs,
    ) -> Message:
        """Calls an OpenAI LLM with a list of messages and returns the response."""

        # ----------------------------------
        # Validate arguments
        # ----------------------------------

        if functions is None:
            functions = []
        if function_call is None:
            function_call = "auto"
        elif function_call not in (
            ["auto", "none"] + [{"name": f.name} for f in functions]
        ):
            raise ValueError(f"Invalid function_call value: {function_call}")
        if logger is None:
            logger = get_logger(self.name)

        # ----------------------------------
        # Form OpenAI-specific arguments
        # ----------------------------------

        openai_messages = [m.as_chat_message() for m in messages]
        openai_functions = [
            f.dict(exclude={"fn"}, exclude_none=True) for f in functions
        ]

        # only add to kwargs if supplied, because empty parameters are not
        # allowed by OpenAI
        if functions:
            kwargs["functions"] = openai_functions
            kwargs["function_call"] = function_call

        # ----------------------------------
        # Call OpenAI LLM
        # ----------------------------------

        response = await openai.ChatCompletion.acreate(
            api_key=marvin.settings.openai_api_key.get_secret_value(),
            model=self.model,
            messages=openai_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True if stream_handler else False,
            **kwargs,
        )

        if stream_handler:
            handler = StreamHandler(callback=stream_handler)
            msg = await handler.handle_streaming_response(response)
            return msg

        else:
            msg = response.choices[0].message.to_dict_recursive()
            return Message(
                role=msg.pop("role").upper(),
                content=msg.pop("content"),
                data=msg,
            )

import json
from logging import Logger
from typing import Any, Callable, Optional, Union

import openai
import openai.openai_object
import tiktoken
from pydantic import BaseModel, Field, validator

import marvin
import marvin.utilities.types
from marvin.models.messages import Message
from marvin.utilities.logging import get_logger

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


class OpenAIFunction(BaseModel):
    name: str
    description: str = None
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    fn: Callable = Field(None, exclude=True)
    args: Optional[dict] = None

    @classmethod
    def from_function(cls, fn: Callable, **kwargs):
        return cls(
            name=kwargs.get("name", fn.__name__),
            description=kwargs.get("description", fn.__doc__),
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


class ChatLLM(BaseModel):
    name: str = None
    model: str = Field(default_factory=lambda: marvin.settings.llm_model)
    max_tokens: int = Field(default_factory=lambda: marvin.settings.llm_max_tokens)
    temperature: float = Field(default_factory=lambda: marvin.settings.llm_temperature)
    stream: bool = Field(default=False)

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

        response: openai.openai_object.OpenAIObject = (
            await openai.ChatCompletion.acreate(
                api_key=marvin.settings.openai_api_key.get_secret_value(),
                model=self.model,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )
        )

        msg = response.choices[0].message.to_dict_recursive()
        return Message(
            role=msg.pop("role").upper(),
            content=msg.pop("content"),
            data=msg,
        )

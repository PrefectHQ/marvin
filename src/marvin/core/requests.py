from typing import Any, ClassVar, Optional, TypeVar

from pydantic import Extra

from .messages import Prompt
from .providers.openai import OpenAIRequestSerializer
from .serializers import AbstractRequestSerializer

R = TypeVar("R", bound="Request")


class Request(Prompt):
    serializer: ClassVar[Any] = OpenAIRequestSerializer()

    def serialize(
        self,
        exclude_none: bool = True,
        exclude_unset: bool = True,
        serializer: Optional[AbstractRequestSerializer] = None,
    ) -> dict[str, Any]:
        # Then, we serialize the messages, functions, and function_call.

        return super().serialize(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            serializer=self.serializer,
        )

    @classmethod
    def from_prompt(
        cls,
        prompt: Prompt,
    ) -> "Request":
        return cls(
            messages=prompt.messages,
            functions=prompt.functions,
            function_call=prompt.function_call,
            response_model=prompt.response_model,
        )

    def __or__(self, __value: "Request") -> "Request":
        messages = (
            self.messages + __value.messages
            if self.messages and __value.messages
            else self.messages or __value.messages
        )
        functions = (
            self.functions + __value.functions
            if self.functions and __value.functions
            else self.functions or __value.functions
        )

        unique_functions = list(
            {
                (
                    function.get("name")
                    if isinstance(function, dict)
                    else function.__name__
                ): function  # noqa
                for function in functions or []
            }.values()
        )

        return self.__class__(
            **{
                **self.dict(
                    exclude={"messages", "functions", "function_call", "response_model"}
                ),  # noqa
                **__value.dict(
                    exclude={"messages", "functions", "function_call", "response_model"}
                ),  # noqa
            },
            messages=messages,  # noqa
            functions=unique_functions,  # noqa
            function_call=__value.function_call or self.function_call,
            response_model=__value.response_model or self.response_model,
        )

    def __ror__(self, __value: "Request") -> "Request":
        messages = (
            self.messages + __value.messages
            if self.messages and __value.messages
            else self.messages or __value.messages
        )
        functions = (
            self.functions + __value.functions
            if self.functions and __value.functions
            else self.functions or __value.functions
        )

        unique_functions = list(
            {
                (
                    function.get("name")
                    if isinstance(function, dict)
                    else function.__name__
                ): function  # noqa
                for function in functions or []
            }.values()
        )

        return self.__class__(
            **{
                **__value.dict(
                    exclude={"messages", "functions", "function_call", "response_model"}
                ),  # noqa
                **self.dict(
                    exclude={"messages", "functions", "function_call", "response_model"}
                ),  # noqa
            },
            messages=messages,  # noqa
            functions=unique_functions,  # noqa
            function_call=self.function_call or __value.function_call,
            response_model=self.response_model or __value.response_model,
        )

    class Config:
        extra = Extra.allow
        validate_assignment = True

from typing import Any, ClassVar

from pydantic import Extra

from .messages import Prompt
from .providers.openai import OpenAIRequestSerializer


class Request(Prompt):
    serializer: ClassVar[Any] = OpenAIRequestSerializer()

    def __enter__(self) -> "Request":
        """Returns self."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Returns None."""
        return None

    def serialize(
        self,
        exclude_none: bool = True,
        exclude_unset: bool = True,
    ) -> dict[str, Any]:
        # Then, we serialize the messages, functions, and function_call.

        return self.__class__.serializer.to_dict(
            messages=self.messages,
            functions=self.functions,
            function_call=self.function_call,
            response_model=self.response_model,
            **self.dict(
                exclude={"messages", "functions", "function_call", "response_model"},
                exclude_none=exclude_none,
                exclude_unset=exclude_unset,
            ),
        )

    class Config:
        extra = Extra.allow
        validate_assignment = True

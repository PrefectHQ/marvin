from typing import Any, Callable, Dict, Literal, Optional

from pydantic import BaseModel

from marvin.core.messages import Message
from marvin.core.serializers import AbstractRequestSerializer
from marvin.core.serializers import json_schema as openai_schema


class AnthropicRequestSerializer(AbstractRequestSerializer):
    def to_dict(
        self,
        /,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,  # noqa
        function_call: Dict[Literal["name"], str] | Literal["auto"] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return super().to_dict(
            messages=messages,
            functions=functions,
            function_call=function_call,
            response_model=response_model,
            **kwargs,
        )

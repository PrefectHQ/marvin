from typing import Any, Callable, Dict, Literal, Optional

from pydantic import BaseModel

from ..messages import Message
from ..serializers import AbstractRequestSerializer, AbstractResponseParser
from ..serializers import json_schema as openai_schema


class OpenAIRequestSerializer(AbstractRequestSerializer):
    @staticmethod
    def serialize_messages(messages: list[Message]) -> list[dict[str, Any]]:
        return [
            {"content": None, **message.dict(exclude_none=True)} for message in messages
        ]  # noqa

    @staticmethod
    def serialize_functions(
        functions: list[Callable[..., Any] | Dict[str, Any] | type[BaseModel]]
    ) -> list[Dict[str, Any]]:
        response: list[Dict[str, Any]] = []
        for function in functions:
            if isinstance(function, dict):
                response.append(function)
            else:
                response.append(openai_schema(function))

        return response

    @staticmethod
    def serialize_function_call(
        function_call: Optional[Literal["auto"] | Dict[Literal["name"], str]]
    ) -> Optional[Literal["auto"] | Dict[Literal["name"], str]]:
        return function_call


class OpenAIResponseParser(AbstractResponseParser):
    @classmethod
    def parse_message(
        cls, choices: Optional[list[dict[str, Any]]] = None, **kwargs: Any
    ) -> dict[str, Message]:
        return {"message": Message(**choice["message"]) for choice in choices or []}

    @classmethod
    def parse_completion_tokens(
        cls, usage: Optional[dict[str, int]] = None, **kwargs: Any
    ) -> dict[str, int]:  # noqa
        return {"completion_tokens": (usage or {}).get("completion_tokens", 0)}

    @classmethod
    def parse_total_tokens(
        cls, usage: Optional[dict[str, int]] = None, **kwargs: Any
    ) -> dict[str, int]:  # noqa
        return {"total_tokens": (usage or {}).get("total_tokens", 0)}

    @classmethod
    def parse_prompt_tokens(
        cls, usage: Optional[dict[str, int]] = None, **kwargs: Any
    ) -> dict[str, int]:
        return {"prompt_tokens": (usage or {}).get("prompt_tokens", 0)}

    @classmethod
    def parse(cls, **kwargs: Any) -> dict[str, Any]:
        return {
            **cls.parse_completion_tokens(**kwargs),
            **cls.parse_total_tokens(**kwargs),
            **cls.parse_prompt_tokens(**kwargs),
            **cls.parse_message(**kwargs),
        }

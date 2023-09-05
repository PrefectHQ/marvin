from typing import Any, Optional

from ..messages import Message
from ..serializers import AbstractRequestSerializer, AbstractResponseParser


class OpenAIRequestSerializer(AbstractRequestSerializer):
    """
    This class is responsible for serializing the request to OpenAI's API.

    This is a subclass of `AbstractRequestSerializer`, which is modeled after
    the OpenAPI specification, which is why this class has no additional
    methods or attributes.
    """

    pass


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

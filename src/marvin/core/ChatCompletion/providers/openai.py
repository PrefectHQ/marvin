from typing import Any, TypeVar

from marvin._compat import cast_to_json, model_dump
from marvin.settings import settings
from pydantic import BaseModel

from ..abstract import AbstractChatCompletion
from ..handlers import Request, Response

T = TypeVar(
    "T",
    bound=BaseModel,
)


class OpenAIChatCompletion(AbstractChatCompletion[T]):
    """
    OpenAI-specific implementation of the ChatCompletion.
    """

    def __init__(self, provider: str, **kwargs: Any):
        super().__init__(defaults=settings.get_defaults(provider or "openai") | kwargs)

    def _serialize_request(self, request: Request[T]) -> dict[str, Any]:
        """
        Serialize the request as per OpenAI's requirements.
        """

        extras = self.defaults | model_dump(
            request,
            exclude={"functions", "function_call", "response_model"},
            exclude_none=True,
        )
        functions: dict[str, Any] = {}
        function_call: Any = {}
        for message in extras.get("messages", []):
            if message.get("name", -1) is None:
                message.pop("name", None)
            if message.get("function_call", -1) is None:
                message.pop("function_call", None)

        if request.response_model:
            schema = cast_to_json(request.response_model)
            functions["functions"] = [schema]
            function_call["function_call"] = {"name": schema.get("name")}

        elif request.functions:
            functions["functions"] = [
                cast_to_json(function) if callable(function) else function
                for function in request.functions
            ]
            if request.function_call:
                function_call["function_call"] = request.function_call
        print("extras", extras)
        return extras | functions | function_call

    def _create_request(self, **kwargs: Any) -> Request[T]:
        """
        Prepare and return an OpenAI-specific request object.
        """
        return Request(**kwargs)

    def _parse_response(self, response: Any) -> Response[T]:
        """
        Parse the response received from OpenAI.
        """
        # Convert OpenAI's response into a standard format or object
        return Response(**response.to_dict_recursive())  # type: ignore

    def _send_request(self, **serialized_request: Any) -> Any:
        """
        Send the serialized request to OpenAI's endpoint/service.
        """
        # Use openai's library functions to send the request and get a response
        # Example:

        import openai

        response = openai.ChatCompletion.create(**serialized_request)  # type: ignore
        return response  # type: ignore

    async def _send_request_async(self, **serialized_request: Any) -> Response[T]:
        """
        Send the serialized request to OpenAI's endpoint asynchronously.
        """
        import openai

        response = await openai.ChatCompletion.acreate(**serialized_request)  # type: ignore # noqa
        return response  # type: ignore

from typing import Any, Callable, Optional, TypeVar, Union

from marvin._compat import cast_to_json, model_dump
from marvin.settings import settings
from marvin.types import Function
from pydantic import BaseModel

from ..abstract import AbstractChatCompletion
from ..handlers import Request, Response

T = TypeVar(
    "T",
    bound=BaseModel,
)


def serialize_function_or_callable(
    function_or_callable: Union[Function, Callable[..., Any]],
    name: Optional[str] = None,
    description: Optional[str] = None,
    field_name: Optional[str] = None,
) -> dict[str, Any]:
    if isinstance(function_or_callable, Function):
        return {
            "name": function_or_callable.__name__,
            "description": function_or_callable.__doc__,
            "parameters": function_or_callable.schema,
        }
    else:
        return cast_to_json(
            function_or_callable,
            name=name,
            description=description,
            field_name=field_name,
        )


class OpenAIChatCompletion(AbstractChatCompletion[T]):
    """
    OpenAI-specific implementation of the ChatCompletion.
    """

    def __init__(self, provider: str, **kwargs: Any):
        super().__init__(defaults=settings.get_defaults(provider or "openai") | kwargs)

    def _serialize_request(
        self, request: Optional[Request[T]] = None
    ) -> dict[str, Any]:
        """
        Serialize the request as per OpenAI's requirements.
        """
        _request = request or Request()
        _request = Request(
            **self.defaults
            | (
                model_dump(
                    request,
                    exclude_none=True,
                )
                if request
                else {}
            )
        )
        _request.function_call = _request.function_call or (
            request and request.function_call
        )
        _request.functions = _request.functions or (request and request.functions)
        _request.response_model = _request.response_model or (
            request and request.response_model
        )  # noqa

        extras = model_dump(
            _request,
            exclude={"functions", "function_call", "response_model"},
        )

        functions: dict[str, Any] = {}
        function_call: Any = {}
        for message in extras.get("messages", []):
            if message.get("name", -1) is None:
                message.pop("name", None)
            if message.get("function_call", -1) is None:
                message.pop("function_call", None)

        if _request.response_model:
            schema = cast_to_json(_request.response_model)
            functions["functions"] = [schema]
            function_call["function_call"] = {"name": schema.get("name")}

        elif _request.functions:
            functions["functions"] = [
                serialize_function_or_callable(function)
                for function in _request.functions
            ]
            if _request.function_call:
                function_call["function_call"] = _request.function_call
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

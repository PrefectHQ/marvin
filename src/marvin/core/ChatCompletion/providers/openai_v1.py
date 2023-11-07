import inspect
from asyncio import create_task
from typing import Any, AsyncGenerator, Callable, Optional, TypeVar, Union

from marvin import settings
from marvin._compat import OPENAI_V1, BaseModel, cast_to_json, model_dump
from marvin.core.ChatCompletion.abstract import AbstractChatCompletion
from marvin.core.ChatCompletion.handlers import Request, Response, Usage
from marvin.types import Function
from marvin.utilities.async_utils import run_sync
from marvin.utilities.messages import Message
from marvin.utilities.streaming import StreamHandler

if OPENAI_V1:

    class OpenAIObject(BaseModel):
        class Config:
            arbitrary_types_allowed = True
            extra = "allow"

        def to_dict_recursive(self) -> dict[str, Any]:
            return model_dump(self, exclude_none=True)

else:
    pass


def make_openai_v1_create_request(request: dict) -> tuple[Callable[..., Any], dict]:
    from openai import AsyncOpenAI

    params = dict(inspect.signature(AsyncOpenAI).parameters)
    return AsyncOpenAI(
        **{k: v for k, v in request.items() if k in params.keys()}
        | {"api_key": settings.openai.api_key.get_secret_value()}
    ).chat.completions.create, {
        k: v for k, v in request.items() if k not in params.keys()
    }


T = TypeVar(
    "T",
    bound=BaseModel,
)

CONTEXT_SIZES = {
    "gpt-3.5-turbo-16k-0613": 16384,
    "gpt-3.5-turbo-16k": 16384,
    "gpt-3.5-turbo-0613": 4096,
    "gpt-3.5-turbo": 4096,
    "gpt-4-32k-0613": 32768,
    "gpt-4-32k": 32768,
    "gpt-4-0613": 8192,
    "gpt-4": 8192,
}


def get_context_size(model: str) -> int:
    if "/" in model:
        model = model.split("/")[-1]

    return CONTEXT_SIZES.get(model, 2048)


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


class OpenAIV1StreamHandler(StreamHandler):
    async def handle_streaming_response(
        self,
        api_response: AsyncGenerator[OpenAIObject, None],
    ) -> OpenAIObject:
        final_chunk = {}
        accumulated_content = ""

        async for r in api_response:
            final_chunk.update(model_dump(r))

            delta = r.choices[0].delta if r.choices and r.choices[0] else None

            if delta is None:
                continue

            accumulated_content += delta.content or ""

            if self.callback:
                callback_result = self.callback(
                    Message(
                        content=accumulated_content, role="assistant", data=final_chunk
                    )
                )
                if inspect.isawaitable(callback_result):
                    create_task(callback_result)

        if "choices" in final_chunk and len(final_chunk["choices"]) > 0:
            final_chunk["choices"][0]["content"] = accumulated_content

        final_chunk["object"] = "chat.completion"

        return OpenAIObject.parse_obj(
            {
                "id": final_chunk["id"],
                "object": final_chunk["object"],
                "created": final_chunk["created"],
                "model": final_chunk["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": accumulated_content,
                        },
                        "finish_reason": "stop",
                    }
                ],
                # TODO: Figure out how to get the usage from the streaming response
                "usage": Usage.parse_obj(
                    {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                ),
            }
        )


class OpenAIV1ChatCompletion(AbstractChatCompletion[T]):
    """
    OpenAI-specific implementation of the ChatCompletion using the v1.x SDK.
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
        return Response(**model_dump(response))  # type: ignore

    def _send_request(self, **serialized_request: Any) -> Any:
        """
        Send the serialized request to OpenAI's endpoint/service.
        """
        # Use openai's library functions to send the request and get a response
        # Example:

        return run_sync(
            self._send_request_async(**serialized_request),
        )

    async def _send_request_async(self, **serialized_request: Any) -> Response[T]:
        """
        Send the serialized request to OpenAI's endpoint asynchronously.
        """
        from openai import AsyncOpenAI

        if handler_fn := serialized_request.pop("stream_handler", {}):
            serialized_request["stream"] = True

        api_key = (
            serialized_request.pop("api_key", None)
            or settings.openai.api_key.get_secret_value()
        )

        response = await AsyncOpenAI(api_key=api_key).chat.completions.create(
            **serialized_request
        )

        if handler_fn:
            response = await OpenAIV1StreamHandler(
                callback=handler_fn,
            ).handle_streaming_response(response)

        return response

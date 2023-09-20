from typing import (
    Any,
    TypeVar,
    Callable,
    Awaitable,
)
import inspect
from marvin._compat import cast_to_json, model_dump
from marvin.settings import settings
from pydantic import BaseModel
from .prompt import render_anthropic_functions_prompt, handle_anthropic_response
from ...abstract import AbstractChatCompletion
from ...handlers import Request, Response

T = TypeVar(
    "T",
    bound=BaseModel,
)


def get_anthropic_create(**kwargs: Any) -> tuple[Callable[..., Any], dict[str, Any]]:
    """
    Get the Anthropic create function and the default parameters,
    pruned of parameters that are not accepted by the constructor.
    """
    import anthropic

    params = dict(inspect.signature(anthropic.Anthropic).parameters)

    return anthropic.Anthropic(
        **{k: v for k, v in kwargs.items() if k in params.keys()}
    ).completions.create, {k: v for k, v in kwargs.items() if k not in params.keys()}


def get_anthropic_acreate(
    **kwargs: Any,
) -> tuple[Callable[..., Awaitable[Any]], dict[str, Any]]:  # noqa
    """
    Get the Anthropic acreate function and the default parameters,
    pruned of parameters that are not accepted by the constructor.
    """
    import anthropic

    params = dict(inspect.signature(anthropic.AsyncAnthropic).parameters)
    return anthropic.AsyncAnthropic(
        **{k: v for k, v in kwargs.items() if k in params.keys()}
    ).completions.create, {k: v for k, v in kwargs.items() if k not in params.keys()}


class AnthropicChatCompletion(AbstractChatCompletion[T]):
    """
    Anthropic-specific implementation of the ChatCompletion.
    """

    def __init__(self, **kwargs: Any):
        """
        Filters out the parameters that are not accepted by the constructor.
        """
        import anthropic

        kwargs = {
            k: v
            for k, v in kwargs.items()
            if k not in dict(inspect.signature(anthropic.Anthropic).parameters).keys()
        }
        super().__init__(defaults=settings.get_defaults("anthropic") | kwargs)

    def _serialize_request(self, request: Request[T]) -> dict[str, Any]:
        """
        Serialize the request as per OpenAI's requirements.
        """

        extras = model_dump(
            request,
            exclude={"messages", "functions", "function_call", "response_model"},
        )
        functions: dict[str, Any] = {}
        function_call: Any = {}

        prompt = "\n\nHuman:"
        for message in request.messages or []:
            if message.role != "function" and message.content:
                prompt += f"\n\n{'Human' if message.role == 'user' else 'Assistant'}"
                prompt += f": {message.content}"

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

        if functions:
            prompt += render_anthropic_functions_prompt(
                functions=functions.pop("functions", []),
                function_call=function_call.pop("function_call", None),
            )

        for message in request.messages or []:
            if message.role == "function":
                prompt += "\n\nAssistant"
                prompt += f": The result of {message.name} is {message.content}."
            if message.function_call:
                prompt += "\n\nAssistant"
                prompt += f": I will call the {message.function_call.name} function."

        prompt += "\n\nAssistant: "
        prompt.replace("\n\nHuman:\n\nHuman: ", "\n\nHuman: ")
        return self.defaults | extras | {"prompt": prompt}

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

        content, function_call = handle_anthropic_response(response.completion)

        return Response(
            **{
                "id": response.log_id,
                "model": response.model,
                "object": "text_completion",
                "created": 0,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "content": content,  # type: ignore
                            "role": "assistant",
                            "function_call": function_call,
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }
        )

    def _send_request(self, **serialized_request: Any) -> Any:
        """
        Send the serialized request to OpenAI's endpoint/service.
        """
        # Use openai's library functions to send the request and get a response
        # Example:
        create, params = get_anthropic_create(**serialized_request)
        response = create(**params)
        return response

    async def _send_request_async(self, **serialized_request: Any) -> Response[T]:
        """
        Send the serialized request to OpenAI's endpoint asynchronously.
        """
        create, params = get_anthropic_acreate(**serialized_request)
        response = await create(**params)
        return response

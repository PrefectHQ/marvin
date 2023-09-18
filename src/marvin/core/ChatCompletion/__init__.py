from marvin import settings
from pydantic import BaseModel, Field
from marvin._compat import model_dump, cast_to_json
from typing import Callable, Any, Awaitable, Optional, Self, Literal
import inspect

"""
    A ChatCompletion object is responsible for exposing a create and acreate method.
"""

_provider_shortcuts = {
    "gpt-3.5-turbo": "openai",
    "gpt-4": "openai",
    "claude-1": "anthropic",
    "claude-2": "anthropic",
}


class Request(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    functions: list[dict[str, Any]] = Field(default_factory=list)
    function_call: Any = None
    response_model: Any = Field(default=None, exclude=True)

    def to_anthropic(self) -> dict[str, Any]:
        response = model_dump(self, exclude={"messages", "functions", "function_call"})

        return response

    def to_openai(self) -> dict[str, Any]:
        response = model_dump(self, exclude={"functions", "function_call"})
        if self.response_model:
            schema = cast_to_json(self.response_model)
            response["functions"] = schema
            response["function_call"] = schema["name"]
        elif self.functions:
            response["functions"] = [cast_to_json(f) for f in self.functions]
            if self.function_call:
                response["function_call"] = self.function_call

        return response

    class Config:
        extra = "allow"


class Message(BaseModel):
    role: str
    content: str


class Response(BaseModel):
    choices: list[Message]

    class Config:
        extra = "allow"


class BaseChatCompletion(BaseModel):
    """
    A ChatCompletion object is responsible for exposing a create and acreate method,
    and for merging default parameters with the parameters passed to these methods.

    :param create: A synchronous function that creates a completion.
    :param acreate: An asynchronous function that creates a completion.
    :param defaults: Default parameters passed to the create and acreate methods.

    """

    create_base: Callable[..., Any] = Field(default=None, repr=False, exclude=True)

    acreate_base: Callable[..., Awaitable[Any]] = Field(
        default=None, repr=False, exclude=True
    )

    request_seriailizer: Callable[..., Any] = Field(
        default=lambda **x: x, repr=False, exclude=True  # type: ignore
    )

    response_parser: Callable[..., Any] = Field(
        default=lambda *x: x, repr=False, exclude=True  # type: ignore
    )

    defaults: dict[str, Any] = Field(default_factory=dict, exclude=True)

    def merge_with_defaults(self, **kwargs: Any) -> dict[str, Any]:
        """
        Merge the passed parameters with the default parameters.
        """
        return self.defaults | kwargs

    def prepare_request(self, **kwargs: Any) -> Request:
        """
        Prepare the request by serializing the parameters.
        """
        return Request(**self.request_seriailizer(**self.merge_with_defaults(**kwargs)))

    def parse_response(self, response: Any) -> Any:
        """
        Parse the response.
        """
        return self.response_parser(response)

    def __call__(self: Self, **kwargs: Any) -> Self:
        """
        Create a new ChatCompletion object with new defaults computed from
        merging the passed parameters with the default parameters.
        """
        copy = self.copy()
        copy.defaults = self.merge_with_defaults(**kwargs)
        return copy

    def create(self, **kwargs: Any) -> Response:
        """
        Create a completion synchronously.
        """
        return self.parse_response(
            self.create_base(**model_dump(self.prepare_request(**kwargs)))
        )

    async def acreate(self, **kwargs: Any) -> Response:
        """
        Create a completion asynchronously.
        """
        return self.parse_response(
            await self.acreate_base(**model_dump(self.prepare_request(**kwargs)))
        )

    def __enter__(self: Self) -> Self:
        """
        Enter a context manager.
        """
        return self

    def __exit__(self: Self, *args: Any) -> None:
        """
        Exit a context manager.
        """
        pass


def parse_model_shortcut(provider: Optional[str]) -> tuple[str, str]:
    """
    Parse a model string into a provider and a model name.
    - If the provider is None, use the default provider and model.
    - If the provider is a shortcut, use the shortcut to get the provider and model.
    """
    if provider is None:
        provider, model = settings.llm_model.split("/", 1)
    elif provider in _provider_shortcuts:
        provider, model = _provider_shortcuts[provider], provider
    else:
        provider, model = provider.split("/", 1)
    return provider, model


def ChatCompletion(
    model: Optional[str] = None,
    create: Optional[Callable[..., Any]] = None,
    acreate: Optional[Callable[..., Awaitable[Any]]] = None,
    request_seriailizer: Optional[Callable[..., Any]] = lambda **x: x,
    response_parser: Optional[Callable[..., Any]] = lambda *x: x,
    **kwargs: Any,
):
    """
    Creates a ChatCompletion object.

    :param model: The model to use. If None, use the default model from settings.
    :param create: A synchronous function that creates a completion.
    :param acreate: An asynchronous function that creates a completion.
    :param kwargs: Parameters that will be passed to every invocation of
                   the create and acreate methods.

    :returns: A ChatCompletion object.

    """

    passed_parameters = {
        **({"create_base": create} if create else {}),
        **({"acreate_base": acreate} if acreate else {}),
        **({"request_seriailizer": request_seriailizer} if request_seriailizer else {}),
        **({"response_parser": response_parser} if response_parser else {}),
    }

    if create and acreate and model is None:
        return BaseChatCompletion(**passed_parameters, defaults=kwargs)

    provider, model_ = parse_model_shortcut(model)

    if provider == "openai" or provider == "azure_openai":
        import openai

        return BaseChatCompletion(
            **{
                **{
                    "create_base": openai.ChatCompletion.create,  # type: ignore
                    "acreate_base": openai.ChatCompletion.create,  # type: ignore
                    "request_seriailizer": lambda response: response.to_dict_recursive(),  # type: ignore # noqa
                },
                **passed_parameters,
            },
            defaults=(
                {"model": model_}
                | settings.get_defaults(provider=provider)
                | kwargs  # type: ignore
            ),
        )

    elif provider == "anthropic":
        """
        Anthropic, unfortunately, requires some parameters to be passed to
        the constructor, and some to the create method. This is because the
        constructor is responsible for creating the async event loop, and
        the create method is responsible for creating the completion.

        So we'll inspect the signature of the constructor and cherry pick
        the parameters that are required for the constructor and the create
        method.
        """

        import anthropic

        async_constructor_params = inspect.signature(
            anthropic.AsyncAnthropic
        ).parameters

        _acreate = anthropic.AsyncAnthropic(
            **{
                k: v
                for k, v in (settings.get_defaults(provider=provider) | kwargs).items()
                if k in async_constructor_params  # type: ignore
            }
        ).completions.create

        constructor_params = inspect.signature(anthropic.Anthropic).parameters

        _create: Callable[..., Any] = anthropic.Anthropic(
            **{
                k: v
                for k, v in (settings.get_defaults(provider=provider) | kwargs).items()
                if k in constructor_params  # type: ignore
            }
        ).completions.create

        return BaseChatCompletion(
            **{
                **{
                    "create_base": _create,
                    "acreate_base": _acreate,  # type: ignore
                },
                **passed_parameters,
            },
            defaults=(
                {"model": model_}
                | {
                    k: v
                    for k, v in (
                        settings.get_defaults(provider=provider) | kwargs
                    ).items()
                    if (
                        k not in constructor_params or k not in async_constructor_params
                    )
                }  # type: ignore
            ),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

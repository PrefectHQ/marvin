from marvin import settings
from pydantic import BaseModel, Field
from marvin._compat import model_dump, cast_to_json, model_copy
from typing import (
    Callable,
    Any,
    Awaitable,
    Optional,
    Self,
    Literal,
    Union,
    overload,
    TypeVar,
    Generic,
    ParamSpec,
)
from functools import wraps
import inspect
from types import FunctionType
from ast import literal_eval
import json

T = TypeVar(
    "T",
    bound=BaseModel,
)

P = ParamSpec("P")


class OpenAISerializer(BaseModel, extra="allow"):
    pass


def parse_raw(raw: str) -> dict[str, Any]:
    try:
        return literal_eval(raw)
    except Exception:
        pass
    try:
        return json.loads(raw)
    except Exception:
        pass
    return {}


class Request(BaseModel, Generic[T], extra="allow", arbitrary_types_allowed=True):
    messages: Optional[list[dict[str, Any]]] = Field(default=None)
    functions: Optional[list[Union[Callable[..., Any], dict[str, Any]]]] = Field(
        default=None
    )
    function_call: Any = None
    response_model: Optional[type[T]] = Field(default=None, exclude=True)

    def serialize(
        self,
        functions_serializer: Callable[
            [Callable[..., Any]], dict[str, Any]
        ] = cast_to_json,
    ) -> dict[str, Any]:
        extras = model_dump(
            self, exclude={"functions", "function_call", "response_model"}
        )
        response_model: dict[str, Any] = {}
        functions: dict[str, Any] = {}
        function_call: dict[str, Any] = {}
        messages: dict[str, Any] = {}

        if self.response_model:
            response_model_schema: dict[str, Any] = functions_serializer(
                self.response_model
            )
            response_model = {
                "functions": [response_model_schema],
                "function_call": {"name": response_model_schema.get("name")},
            }

        elif self.functions:
            functions = {
                "functions": [
                    functions_serializer(function) if callable(function) else function
                    for function in self.functions
                ]
            }
            if self.function_call:
                functions["function_call"] = self.function_call

        return extras | functions | function_call | messages | response_model

    def function_registry(
        self, serializer: Callable[[Callable[..., Any]], dict[str, Any]] = cast_to_json
    ) -> dict[str, FunctionType]:
        return {
            serializer(function).get("name", ""): function
            for function in self.functions or []
            if isinstance(function, FunctionType)
        }


class FunctionCall(BaseModel):
    name: str
    arguments: str


class Message(BaseModel):
    content: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    function_call: Optional[FunctionCall] = Field(default=None)


class Choice(BaseModel):
    message: Message
    index: int
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Response(BaseModel, Generic[T], extra="allow", arbitrary_types_allowed=True):
    id: str
    object: str
    created: int
    model: str
    usage: Usage
    choices: list[Choice] = Field(default_factory=list)


class Turn(BaseModel, Generic[T], extra="allow", arbitrary_types_allowed=True):
    request: Request[T]
    response: Response[T]

    @overload
    def __getitem__(self, key: Literal[0]) -> Request[T]:
        ...

    @overload
    def __getitem__(self, key: Literal[1]) -> Response[T]:
        ...

    def __getitem__(self, key: int) -> Union[Request[T], Response[T]]:
        if key == 0:
            return self.request
        elif key == 1:
            return self.response
        else:
            raise IndexError("Turn only has two items.")

    def has_function_call(self) -> bool:
        return any([choice.message.function_call for choice in self.response.choices])

    def get_function_call(self) -> list[tuple[str, dict[str, Any]]]:
        if not self.has_function_call():
            raise ValueError("No function call found.")
        pairs: list[tuple[str, dict[str, Any]]] = []
        for choice in self.response.choices:
            if choice.message.function_call:
                pairs.append(
                    (
                        choice.message.function_call.name,
                        parse_raw(choice.message.function_call.arguments),
                    )
                )
        return pairs

    def call_function(self) -> Any:
        if not self.has_function_call():
            raise ValueError("No function call found.")
        pairs: list[tuple[str, dict[str, Any]]] = self.get_function_call()
        function_registry: dict[str, FunctionType] = self.request.function_registry()
        evaluations: list[Any] = []
        for pair in pairs:
            name, argument = pair
            if name not in function_registry:
                raise ValueError(f"Function {name} not found in function registry.")
            evaluations.append(function_registry[name](**argument))
        if len(evaluations) == 1:
            return evaluations[0]
        else:
            return evaluations

    def to_model(self) -> T:
        if not self.request.response_model:
            raise ValueError("No response model found.")
        model = self.request.response_model
        pairs = self.get_function_call()
        return model(**pairs[0][1])


class Conversation(BaseModel, Generic[T], extra="allow", arbitrary_types_allowed=True):
    turns: list[Turn[T]]
    model: "BaseChatCompletion[T]"

    def __getitem__(self, key: int) -> Turn[T]:
        return self.turns[key]

    @property
    def last_turn(self) -> Turn[T]:
        return self.turns[-1]

    @property
    def last_request(self) -> Request[T]:
        return self.last_turn[0]

    @property
    def last_response(self) -> Response[T]:
        return self.last_turn[1]

    def send(self, **kwargs: Any) -> Turn[T]:
        turn = self.model.create(**kwargs)
        self.turns.append(turn)
        return turn

    async def asend(self, **kwargs: Any) -> Turn[T]:
        turn = await self.model.acreate(**kwargs)
        self.turns.append(turn)
        return turn


_provider_shortcuts = {
    "gpt-3.5-turbo": "openai",
    "gpt-4": "openai",
    "claude-1": "anthropic",
    "claude-2": "anthropic",
}


class BaseChatCompletion(BaseModel, extra="allow", arbitrary_types_allowed=True):
    """
    A ChatCompletion object is responsible for exposing a create and acreate method,
    and for merging default parameters with the parameters passed to these methods.

    :param create: A synchronous function that creates a completion.
    :param acreate: An asynchronous function that creates a completion.
    :param defaults: Default parameters passed to the create and acreate methods.

    """

    call: Callable[..., Any] = Field(default=None, repr=False, exclude=True)

    acall: Callable[..., Awaitable[Any]] = Field(default=None, repr=False, exclude=True)

    defaults: dict[str, Any] = Field(default_factory=dict, exclude=True)

    def get_messages_serializer(
        self,
    ) -> Callable[..., dict[str, Any]]:
        """
        Get the serializer.
        """
        return lambda **x: x

    def get_functions_serializer(
        self,
    ) -> Callable[[Callable[..., Any]], dict[str, Any]]:
        """
        Get the serializer.
        """
        return cast_to_json

    def merge_with_defaults(self, **kwargs: Any) -> dict[str, Any]:
        """
        Merge the passed parameters with the default parameters.
        """
        return self.defaults | kwargs

    def prepare_request(
        self, response_model: Optional[type[T]], **kwargs: Any
    ) -> Request[T]:  # noqa
        """
        Prepare the request by serializing the parameters.
        """
        return Request(
            **self.merge_with_defaults(**kwargs, response_model=response_model)
        )

    def parse_response(self, response: Any) -> Any:
        """
        Parse the response.
        """
        return response

    def __call__(self: Self, **kwargs: Any) -> Self:
        """
        Create a new ChatCompletion object with new defaults computed from
        merging the passed parameters with the default parameters.
        """
        copy = model_copy(self)
        copy.defaults = self.merge_with_defaults(**kwargs)
        return copy

    def create(
        self, response_model: Optional[type[T]] = None, **kwargs: Any
    ) -> Turn[T]:
        """
        Create a completion synchronously.
        """
        request = self.prepare_request(**kwargs, response_model=response_model)

        return Turn(
            request=request,
            response=self.call(
                **request.serialize(
                    functions_serializer=self.get_functions_serializer()
                )
            ),
        )

    async def acreate(
        self, response_model: Optional[type[T]] = None, **kwargs: Any
    ) -> Turn[T]:
        """
        Create a completion asynchronously.
        """
        request = self.prepare_request(**kwargs, response_model=response_model)
        response = await self.acall(
            **request.serialize(functions_serializer=self.get_functions_serializer())
        )
        return Turn(request=request, response=response)

    def __enter__(self: Self) -> Conversation[BaseModel]:
        """
        Enter a context manager.
        """
        return Conversation(turns=[], model=self)

    def __exit__(self: Self, *args: Any) -> None:
        """
        Exit a context manager.
        """
        pass


def messages_to_transcript(messages: list[Message]) -> str:
    """
    Convert a list of messages to a transcript.
    """
    return (
        "\n\n".join(
            [
                f"\n\n{'Human' if message.role == 'user' else 'Assistant'}: {message.content}"  # noqa
                for message in messages
                if message.content
            ]
        )
        + '\n\nAssistant: "'
    )


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


def get_openai_create(**kwargs: Any) -> tuple[Callable[..., Any], dict[str, Any]]:
    """
    Get the OpenAI create function and the default parameters,
    pruned of parameters that are not accepted by the constructor.
    """
    import openai

    return openai.ChatCompletion.create, kwargs  # type: ignore


def get_openai_acreate(
    **kwargs: Any,
) -> tuple[Callable[..., Awaitable[Any]], dict[str, Any]]:  # noqa
    """
    Get the OpenAI acreate function and the default parameters,
    pruned of parameters that are not accepted by the constructor.
    """
    import openai

    return openai.ChatCompletion.acreate, kwargs  # type: ignore


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


def ChatCompletion(
    model: Optional[str] = None,
    create: Optional[Callable[..., Any]] = None,
    acreate: Optional[Callable[..., Awaitable[Any]]] = None,
    **kwargs: Any,
) -> BaseChatCompletion:  # type: ignore
    """
    Creates a ChatCompletion object. This is functionally a __init__ method
    for the ChatCompletion class.

    :param model: The model to use. If None, use the default model from settings.
    :param create: A synchronous function that creates a completion.
    :param acreate: An asynchronous function that creates a completion.
    :param kwargs: Parameters that will be passed to every invocation of
                   the create and acreate methods.

    :returns: A ChatCompletion object.

    """
    if create and acreate and model is None:
        return BaseChatCompletion(call=create, acall=acreate, defaults=kwargs)

    provider, model_ = parse_model_shortcut(model)

    if provider == "openai" or provider == "azure_openai":
        settings_defaults = settings.get_defaults(provider=provider)
        call, _ = get_openai_create(**settings_defaults | kwargs)
        acall, _ = get_openai_acreate(**settings_defaults | kwargs)

        return BaseChatCompletion(
            call=call,
            acall=acall,
            defaults=({"model": model_} | settings_defaults | kwargs),  # type: ignore
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
        settings_defaults = settings.get_defaults(provider=provider)
        call, pruned_kwargs = get_anthropic_create(**kwargs)
        acall, _ = get_anthropic_acreate(**kwargs)
        return BaseChatCompletion(
            call=call,
            acall=acall,
            defaults=(
                {"model": model_}
                | settings.get_defaults(provider=provider)
                | pruned_kwargs  # type: ignore
            ),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

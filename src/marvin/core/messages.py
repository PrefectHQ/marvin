import json
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

from pydantic import BaseModel, Field, Json, PrivateAttr

from ..utilities.strings import jinja_env

if TYPE_CHECKING:
    from .serializers import AbstractRequestSerializer
import inspect
import re
from enum import Enum
from functools import partial, wraps

from jinja2 import Environment, meta
from marvin.types import ParamSpec
from marvin.utilities.types import ResponseModel

P = ParamSpec("P")  # requires python >= 3.10


R = TypeVar("R")

M = TypeVar("M", bound="Message")
T = TypeVar("T", bound="Prompt")


class Role(Enum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    HUMAN = "user"
    FUNCTION = "function"


class FunctionCall(BaseModel):
    name: str = Field(default=None)
    arguments: Json[dict[str, Any]] = Field(default=None)

    def dict(self, round_trip: bool = True, **kwargs: Any) -> dict[str, Any]:
        response = super().dict(**kwargs)
        response["arguments"] = json.dumps(response["arguments"])
        return response


class Message(BaseModel):
    env: ClassVar[Environment] = jinja_env
    role: Optional[Literal["system", "assistant", "user", "function"]] = Field(
        default="system"
    )
    content: Optional[str] = Field(default=None)
    function_call: Optional[FunctionCall] = Field(default=None, repr=False)
    name: Optional[str] = Field(default=None, repr=False)

    def __or__(self, *args: Union[None, "Message", list["Message"]]):
        response: list[Message] = []
        for arg in args:
            if isinstance(arg, list):
                response.extend(arg)
            elif arg is not None:
                response.append(arg)
            else:
                pass
        return MessageList([self, *response])

    def __ror__(self, *args: Union[None, "Message", list["Message"]]):
        response: list[Message] = []
        for arg in args:
            if isinstance(arg, list):
                response.extend(arg)
            elif arg is not None:
                response.append(arg)
            else:
                pass
        return MessageList([*response, self])

    @classmethod
    def from_string(
        cls: type[M],
        text: str,
        role: Optional[Literal["system", "user", "assistant", "function"]] = None,
    ) -> M:
        return cls(role=role, content=text)

    def render(
        self: M,
        **kwargs: Any,
    ) -> M:
        return Message(
            **{
                **self.dict(),  # type: ignore
                "content": (
                    self.env.from_string(self.content or "").render(**kwargs).strip()
                ),
            }
        )


class MessageList(list[Message]):
    def dict(self, exclude_none: bool = True, **kwargs: Any) -> list[dict[str, Any]]:
        return [message.dict(exclude_none=exclude_none, **kwargs) for message in self]

    def render(
        self,
        **kwargs: Any,
    ) -> "MessageList":
        return MessageList([message.render(**kwargs) for message in self])

    def __or__(self, *args: Optional[Union["Message", list["Message"]]]):
        response: list[Message] = []
        for arg in args:
            if isinstance(arg, list):
                response.extend(arg)
            elif arg is not None:
                response.append(arg)
            else:
                pass
        return MessageList([*self, *response])

    def __ror__(self, *args: Optional[Union["Message", list["Message"]]]):
        response: list[Message] = []
        for arg in args:
            if isinstance(arg, list):
                response.extend(arg)
            elif arg is not None:
                response.append(arg)
            else:
                pass
        return MessageList([*response, *self])


class Prompt(BaseModel):
    env: ClassVar[Environment] = jinja_env

    _context: dict[str, Any] = PrivateAttr(default_factory=dict)

    messages: list[Message] = Field(default_factory=MessageList)
    functions: Optional[list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]] = (
        None
    )
    function_call: Optional[Union[Literal["auto"], dict[Literal["name"], str]]] = None
    response_model: Optional[type[BaseModel]] = None

    def render(
        self: T,
        **kwargs: Any,
    ) -> T:
        """
        Renders the request's messages using the provided keyword arguments,
        functions, function_call, and response_model. Returns a new Request object
        with the rendered messages.
        """

        copy = self.copy()
        copy.messages = MessageList(self.messages).render(
            **self._context,
            **kwargs,
            functions=self.functions,
            function_call=self.function_call,
            response_model=self.response_model,
        )
        return copy

    def serialize(
        self,
        exclude_none: bool = True,
        exclude_unset: bool = True,
        serializer: Optional["AbstractRequestSerializer"] = None,
    ) -> dict[str, Any]:
        # Then, we serialize the messages, functions, and function_call.
        if not serializer:
            from .providers.openai import OpenAIRequestSerializer

            serializer = OpenAIRequestSerializer()

        return serializer.to_dict(
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

    @classmethod
    def from_string(
        cls,
        text: str,
        role: Literal["system", "user", "assistant", "function"] = "user",
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        ] = None,
        function_call: Optional[Literal["auto"] | dict[Literal["name"], str]] = None,
        response_model: Optional[type[BaseModel]] = None,
    ):
        return cls(
            messages=[Message.from_string(text, role=role)],
            functions=functions,
            function_call=function_call,
            response_model=response_model,
        )

    def dict(self, exclude_none: bool = True, **kwargs: Any) -> dict[str, Any]:
        return super().dict(exclude_none=exclude_none, **kwargs)


def validate_template(
    func: Callable[P, Any],
    template: Optional[str] = None,
    ctx: Optional[dict[str, Any]] = None,
    environment: Environment | None = None,
) -> bool:
    # If environment is not provided, create a new one.
    env = environment or Environment()

    # Get the signature of the function
    signature = inspect.signature(func)
    signature_params = set(signature.parameters.keys()).union(
        {"response_model", "__self__", "__params__"}
    )
    context_params = set((ctx or {}).keys())

    # Get the undeclared variables in the docstring
    string_template: str = template or func.__doc__ or ""
    template_params = meta.find_undeclared_variables(env.parse(string_template))

    # Check if the signature and context contain all the variables in the template
    return signature_params.union(context_params).issuperset(template_params)


@overload
def prompt(
    *,
    environment: Environment | None = None,
    ctx: dict[str, Any] | None = None,
    strict: bool = True,
    roles: type[Enum] | None = Role,
    response_model: type[BaseModel] | None = None,
) -> Callable[[Callable[P, None]], Callable[P, Prompt]]:
    pass


@overload
def prompt(
    func: Callable[P, Any],
    *,
    environment: Environment | None = None,
    ctx: dict[str, Any] | None = None,
    strict: bool = True,
    roles: type[Enum] | None = Role,
    response_model: type[BaseModel] | None = None,
) -> Callable[P, Prompt]:
    pass


def prompt(
    func: Optional[Callable[P, Any]] = None,
    *,
    environment: Environment | None = None,
    ctx: dict[str, Any] | None = None,
    strict: bool = True,
    roles: type[Enum] | None = Role,
    response_model: type[BaseModel] | None = None,
) -> Union[
    Callable[[Callable[P, None]], Callable[P, None]],
    Callable[[Callable[P, None]], Callable[P, Prompt]],
    Callable[P, Prompt],
]:
    env = environment or Environment()
    ctx = ctx or {}

    def wrapper(func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> Prompt:
        """The actual logic"""
        # Do something with first and second and produce a `result` of type `R`
        signature = inspect.signature(func)
        _response_model = response_model or ResponseModel.from_type(
            type_=signature.return_annotation,
        )
        params = signature.bind(*args, **kwargs)
        params.apply_defaults()
        # regex_group = '|'.join([f'{role.name.upper()}:' for role in role])
        rendered_template = inspect.cleandoc(
            env.from_string(func.__doc__ or "").render(
                **ctx,
                **params.arguments,
                __self__=func,
                __params__=params.arguments,
                response_model=_response_model,
            )
        ).strip()
        if rendered_template.split(":")[0].upper() not in [
            role.name for role in roles or Role
        ]:
            rendered_template = next(iter(Role)).name + ": " + rendered_template
        regex_group = "|".join([f"{role.name.upper()}:" for role in roles or Role])
        return Prompt(
            messages=[
                {
                    "role": (roles or Role)[name.strip()[:-1]].value,
                    "content": value.strip(),
                }
                for (name, value) in re.findall(
                    f"({regex_group})(.*?)(?=\s*(?:{regex_group}|$))",  # type: ignore
                    "\n\n" + rendered_template,
                    flags=re.DOTALL,
                )
            ],
            response_model=_response_model,
        )

    # Without arguments `func` is passed directly to the decorator
    if func is not None:
        if not callable(func):
            raise TypeError("Not a callable. Did you use a non-keyword argument?")
        if strict and not validate_template(func=func, ctx=ctx, environment=env):
            raise TypeError("YOOOO!")
        return wraps(func)(partial(wrapper, func))

    # With arguments, we need to return a function that accepts the function
    def decorator(func: Callable[P, None]) -> Callable[P, Prompt]:
        return wraps(func)(partial(wrapper, func))

    return decorator

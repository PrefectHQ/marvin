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
)

from jinja2 import Environment
from pydantic import BaseModel, Field, Json, PrivateAttr

from ..utilities.strings import jinja_env

if TYPE_CHECKING:
    from .serializers import AbstractRequestSerializer

M = TypeVar("M", bound="Message")
T = TypeVar("T", bound="Prompt")


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
    function_call: Optional[FunctionCall] = Field(default=None)
    name: Optional[str] = Field(default=None)

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

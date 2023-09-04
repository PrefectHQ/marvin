from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Literal,
    Optional,
    Union,
)

import openai
from marvin import settings
from pydantic import BaseModel, Extra, Field

from .messages import Message
from .requests import Request
from .responses import Response, Turn

if TYPE_CHECKING:
    from .conversations import Conversation


class ChatCompletionConfig(Request):
    create: ClassVar[Callable[..., Any]] = openai.ChatCompletion.create  # type: ignore
    acreate: ClassVar[Callable[..., Awaitable[Any]]] = openai.ChatCompletion.acreate  # type: ignore # noqa

    api_key: Optional[str] = getattr(
        settings.openai.api_key, "get_secret_value", lambda: None
    )()  # noqa

    model: str = "gpt-3.5-turbo"

    class Config(Request.Config):
        extra = Extra.allow


class BaseChatCompletion(BaseModel):
    defaults: ChatCompletionConfig = Field(
        default=ChatCompletionConfig(),
        exclude=True,
        repr=False,
    )

    def prepare_request(
        self,
        messages: Optional[list[Message]] = None,
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | BaseModel]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Request:
        params = self.defaults.dict(
            exclude={"response_model", "functions", "function_call", "messages"}
        )

        request = Request(
            **(params | self.dict() | kwargs),
            messages=[*(self.defaults.messages or []), *(messages or [])],
            functions=[*(self.defaults.functions or []), *(functions or [])],
            function_call=function_call or self.defaults.function_call,
            response_model=response_model or self.defaults.response_model,
        )
        return request

    def create(
        self,
        messages: Optional[list[Message]] = None,
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | BaseModel]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Turn:
        request = self.prepare_request(
            messages=messages,
            functions=functions,
            function_call=function_call,
            response_model=response_model,
            **kwargs,
        )

        return Turn(
            request=request,
            response=Response(**self.defaults.create(**request.serialize())),
        )

    def chain(
        self,
        messages: Optional[list[Message]] = None,
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | BaseModel]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> "Conversation":
        with self as conversation:
            conversation.send(
                messages=messages,
                functions=functions,
                function_call=function_call,
                response_model=response_model,
                **kwargs,
            )
            while conversation.turns[-1].response.has_function_call:
                conversation.send(
                    messages=[conversation.turns[-1].call_function()],
                    functions=functions,
                    function_call=function_call,
                    response_model=response_model,
                    **kwargs,
                )
        return conversation

    async def achain(
        self,
        messages: Optional[list[Message]] = None,
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | BaseModel]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> "Conversation":
        with self as conversation:
            await conversation.asend(
                messages=messages,
                functions=functions,
                function_call=function_call,
                response_model=response_model,
                **kwargs,
            )
            while conversation.turns[-1].response.has_function_call:
                await conversation.asend(
                    messages=[conversation.turns[-1].call_function()],
                    functions=functions,
                    function_call=function_call,
                    response_model=response_model,
                    **kwargs,
                )
        return conversation

    async def acreate(
        self,
        messages: Optional[list[Message]] = None,
        functions: Optional[
            list[Callable[..., Any] | dict[str, Any] | BaseModel]
        ] = None,  # noqa
        function_call: Optional[
            Union[Literal["auto"], dict[Literal["name"], str]]
        ] = None,  # noqa
        response_model: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Turn:
        request = self.prepare_request(
            messages=messages,
            functions=functions,
            function_call=function_call,
            response_model=response_model,
            **kwargs,
        )

        return Turn(
            request=request,
            response=Response(**await self.defaults.acreate(**request.serialize())),
        )

    def __enter__(self) -> "Conversation":
        """Returns self."""
        from .conversations import Conversation

        return Conversation(model=self)

    def __exit__(self, *args: Any) -> None:
        """Returns None."""
        return None


def ChatCompletion(
    model: str,
    messages: Optional[list[Message]] = None,
    functions: Optional[
        list[Callable[..., Any] | dict[str, Any] | BaseModel]
    ] = None,  # noqa
    function_call: Optional[
        Union[Literal["auto"], dict[Literal["name"], str]]
    ] = None,  # noqa
    response_model: Optional[type[BaseModel]] = None,
    **kwargs: Any,
) -> BaseChatCompletion:
    response = BaseChatCompletion(
        defaults=ChatCompletionConfig.construct(
            model=model,
            messages=messages,
            functions=functions,
            function_call=function_call,
            response_model=response_model,
            **kwargs,
        )
    )
    return response

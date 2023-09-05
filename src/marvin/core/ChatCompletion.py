from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Literal,
    Optional,
    Union,
    overload,
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

    @overload
    def __call__(
        self,
        request: Optional[Request] = None,
    ) -> "BaseChatCompletion":
        """
        Implements the core logic to create a new ChatCompletion object based on
        the provided parameters or request object. This method merges the
        provided parameters with existing defaults.

        Args:
            request (Optional[Request]): A request object.
            messages (list[Message] | None): A list of messages.
            functions (list[Callable[..., Any]|dict[str, Any]|BaseModel] | None): A list of functions.
            function_call (Literal["auto"] | dict[Literal["name"], str] | None): A function call.
            response_model (type[BaseModel] | None): A response model.
            **kwargs: Additional keyword arguments.

        Returns:
            BaseChatCompletion: A new ChatCompletion object with defaults set to the merged
            values of the existing defaults and provided parameters.
        """  # noqa

    @overload
    def __call__(
        self,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> "BaseChatCompletion":
        """
        Implements the core logic to create a new ChatCompletion object based on
        the provided parameters or request object. This method merges the
        provided parameters with existing defaults.

        Args:
            request (Optional[Request]): A request object.
            messages (list[Message] | None): A list of messages.
            functions (list[Callable[..., Any]|dict[str, Any]|BaseModel] | None): A list of functions.
            function_call (Literal["auto"] | dict[Literal["name"], str] | None): A function call.
            response_model (type[BaseModel] | None): A response model.
            **kwargs: Additional keyword arguments.

        Returns:
            BaseChatCompletion: A new ChatCompletion object with defaults set to the merged
            values of the existing defaults and provided parameters.
        """  # noqa

    def __call__(
        self,
        request: Optional[Request] = None,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ):
        """
        Implements the core logic to create a new ChatCompletion object based on
        the provided parameters or request object. This method merges the
        provided parameters with existing defaults.

        Args:
            request (Optional[Request]): A request object.
            messages (list[Message] | None): A list of messages.
            functions (list[Callable[..., Any]|dict[str, Any]|BaseModel] | None): A list of functions.
            function_call (Literal["auto"] | dict[Literal["name"], str] | None): A function call.
            response_model (type[BaseModel] | None): A response model.
            **kwargs: Additional keyword arguments.

        Returns:
            BaseChatCompletion: A new ChatCompletion object with defaults set to the merged
            values of the existing defaults and provided parameters.
        """  # noqa

        # Perform shallow copy as to not mutate the original object.
        _self = self.copy()

        # If a request object is passed, return a new ChatCompletion object
        if request:
            # Merge the request object's parameters with the existing defaults.
            return _self.__class__(
                defaults=ChatCompletionConfig(**(self.defaults | request).dict())
            )
        else:
            # Create a new request object with the provided parameters.
            # Merge the request object's parameters with the existing defaults.
            return _self.__class__(
                defaults=ChatCompletionConfig(
                    **(
                        self.defaults
                        | Request(
                            messages=messages or [],
                            functions=functions,
                            function_call=function_call,
                            response_model=response_model,
                            **kwargs,
                        )
                    ).dict()
                )
            )

    @overload
    def prepare_request(
        self,
        request: Optional[Request] = None,
    ) -> Request:
        """
        Prepare a Request object together with the provided default values
        of the ChatCompletion object.

        Args:
            request (Optional[Request]): A request object.

        Returns:
            Request: A prepared Request object.

        """  # noqa

    @overload
    def prepare_request(
        self,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Request:
        """
        Prepare a Request object together with the provided default values
        of the ChatCompletion object.

        Args:
            messages (list[Message] | None): A list of messages.
            functions (list[Callable[..., Any]|dict[str, Any]|BaseModel] | None): A list of functions.
            function_call (Literal["auto"] | dict[Literal["name"], str] | None): A function call.
            response_model (type[BaseModel] | None): A response model.
            **kwargs: Additional keyword arguments.

        Returns:
            Request: A prepared Request object.

        """  # noqa

    def prepare_request(
        self,
        request: Optional[Request] = None,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Request:
        return Request(
            **self(
                request=request,
                messages=messages,
                functions=functions,
                function_call=function_call,
                response_model=response_model,
                **kwargs,
            ).defaults.dict()
        )

    @overload
    def create(
        self,
        request: Optional[Request] = None,
    ) -> Turn:
        pass
        """
        Passes the provided request object to the ChatCompletion object's create method.

        Args:
            request (Optional[Request]): A request object.

        Returns:
            Turn: A Turn object.
        """

    @overload
    def create(
        self,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Turn:
        """
        Passes the provided request parameters to the ChatCompletion object's create method.

        Args:
            - messages (list[Message] | None): A list of messages.
            - functions (list[Callable[..., Any]|dict[str, Any]|BaseModel] | None): A list of functions.
            - function_call (Literal["auto"] | dict[Literal["name"], str] | None): A function call.
            - response_model (type[BaseModel] | None): A response model.
            - **kwargs: Additional keyword arguments.

        Returns:
            Turn: A Turn object.
        """  # noqa

    def create(
        self,
        request: Optional[Request] = None,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Turn:
        request = self.prepare_request(
            request=request,
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

    @overload
    async def acreate(
        self,
        request: Optional[Request] = None,
    ) -> Turn:
        """
        Passes the provided request object to the ChatCompletion object's acreate method.

        Args:
            - request (Optional[Request]): A request object.

        Returns:
            Turn: A Turn object.
        """  # noqa

    @overload
    async def acreate(
        self,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Turn:
        """
        Passes the provided request parameters to the ChatCompletion object's acreate method.

        Args:
            - messages (list[Message] | None): A list of messages.
            - functions (list[Callable[..., Any]|dict[str, Any]|BaseModel] | None): A list of functions.
            - function_call (Literal["auto"] | dict[Literal["name"], str] | None): A function call.
            - response_model (type[BaseModel] | None): A response model.
            - **kwargs: Additional keyword arguments.

        Returns:
            Turn: A Turn object.
        """  # noqa

    async def acreate(
        self,
        request: Optional[Request] = None,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Turn:
        request = self.prepare_request(
            request=request,
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

    @overload
    def chain(
        self,
        request: Optional[Request] = None,
        *,
        until: Optional[Callable[[Turn], bool]] = None,
    ) -> "Conversation":
        pass

    @overload
    def chain(
        self,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        until: Optional[Callable[[Turn], bool]] = None,
        **kwargs: Any,
    ) -> "Conversation":
        pass

    def __enter__(self) -> "Conversation":
        from .conversations import Conversation

        return Conversation(model=self)

    def __exit__(self, *args: Any) -> None:
        pass

    def chain(
        self,
        request: Optional[Request] = None,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        until: Optional[Callable[[Turn], bool]] = None,
        **kwargs: Any,
    ) -> "Conversation":
        with self as conversation:
            conversation.send(
                request=request,
                messages=messages,
                functions=functions,
                function_call=function_call,
                response_model=response_model,
                **kwargs,
            )
            while conversation.turns[-1].response.has_function_call and (
                not until or not until(conversation.turns[-1])
            ):  # noqa
                conversation.send(
                    messages=[conversation.turns[-1].call_function()],
                    functions=functions,
                    function_call=function_call,
                    response_model=response_model,
                    **kwargs,
                )
        return conversation

    @overload
    async def achain(
        self,
        request: Optional[Request] = None,
    ) -> "Conversation":
        pass

    @overload
    async def achain(
        self,
        *,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        until: Optional[Callable[[Turn], bool]] = None,
        **kwargs: Any,
    ) -> "Conversation":
        pass

    async def achain(
        self,
        request: Optional[Request] = None,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        until: Optional[Callable[[Turn], bool]] = None,
        **kwargs: Any,
    ) -> "Conversation":
        with self as conversation:
            await conversation.asend(
                request=request,
                messages=messages,
                functions=functions,
                function_call=function_call,
                response_model=response_model,
                **kwargs,
            )
            while conversation.turns[-1].response.has_function_call and (
                not until or not until(conversation.turns[-1])
            ):  # noqa
                await conversation.asend(
                    messages=[conversation.turns[-1].call_function()],
                    functions=functions,
                    function_call=function_call,
                    response_model=response_model,
                    **kwargs,
                )
        return conversation


@overload
def ChatCompletion(
    model: Optional[str] = None,
    defaults: Optional[Request] = None,
) -> BaseChatCompletion:
    pass


@overload
def ChatCompletion(
    model: Optional[str] = None,
    *,
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
    pass


def ChatCompletion(
    model: Optional[str] = None,
    defaults: Optional[Request] = None,
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
    if defaults:
        response = BaseChatCompletion(
            defaults=ChatCompletionConfig.construct(
                model=model or getattr(defaults, "model", None) or "gpt-3.5-turbo",
                **defaults.dict(),
                **kwargs,
            )
        )
    else:
        response = BaseChatCompletion(
            defaults=ChatCompletionConfig.construct(
                model=model or "gpt-3.5-turbo",
                messages=messages or [],
                functions=functions,
                function_call=function_call,
                response_model=response_model,
                **kwargs,
            )
        )
    return response

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

from pydantic import BaseModel, Extra, Field

from .messages import Message
from .requests import Request
from .responses import Response, Turn

if TYPE_CHECKING:
    from .conversations import Conversation


class ChatCompletionConfig(Request):
    create: ClassVar[Callable[..., Any]]
    acreate: ClassVar[Callable[..., Awaitable[Any]]]

    api_key: str | None = Field(default=None)

    model: str | None = Field(default=None)

    class Config(Request.Config):
        extra = Extra.allow


class BaseChatCompletion(BaseModel):
    defaults: ChatCompletionConfig = Field(
        default_factory=ChatCompletionConfig,  # type: ignore
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
        create: Optional[Callable[..., Any]] = None,
        acreate: Optional[Callable[..., Awaitable[Any]]] = None,
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
        defaults = type(
            "ChatCompletionConfig",
            (ChatCompletionConfig,),
            {
                "create": create or self.defaults.create,
                "acreate": acreate or self.defaults.acreate,
            },
        )(
            **(
                self.defaults
                | (
                    request
                    or Request(
                        messages=messages or [],
                        functions=functions,
                        function_call=function_call,
                        response_model=response_model,
                        **kwargs,
                    )
                )
            ).dict()
        )
        return BaseChatCompletion(defaults=defaults)

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

    @overload
    def create(
        self,
        *,
        preview: bool = True,
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

    @overload
    def create(
        self,
        *,
        preview: bool = True,
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
        preview: bool = False,
        **kwargs: Any,
    ) -> Turn | Request:
        request = self.prepare_request(
            request=request,
            messages=messages,
            functions=functions,
            function_call=function_call,
            response_model=response_model,
            **kwargs,
        )

        if preview:
            return request

        raw_response = self.defaults.create(**request.serialize())
        return Turn(
            request=request,
            response=Response(**raw_response),
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


_provider_shortcuts = {
    "gpt-3.5-turbo": "openai",
    "gpt-4": "openai",
    "claude-1": "anthropic",
    "claude-2": "anthropic",
}


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
    create: Optional[Callable[..., Any]] = None,
    acreate: Optional[Callable[..., Awaitable[Any]]] = None,
    **kwargs: Any,
) -> BaseChatCompletion:
    if not model:
        from marvin import settings

        model = settings.llm_model

    if model in _provider_shortcuts:
        provider, model = _provider_shortcuts[model], model

    else:
        provider, model = model.split("/", 1)

    if provider == "openai":
        from marvin import settings

        base = settings.openai.ChatCompletion(
            model=model,
        )

    elif provider == "anthropic":
        from marvin import settings

        base = settings.anthropic.ChatCompletion(
            model=model,
        )

    elif provider == "azure_openai":
        from marvin import settings

        base = settings.azure_openai.ChatCompletion(
            model=model,
        )

    else:
        base = BaseChatCompletion(
            defaults=type(
                "ChatCompletionConfig",
                (ChatCompletionConfig,),
                {
                    "create": create,
                    "acreate": acreate,
                },
            )()
        )

    return base(
        model=model,
        request=defaults,
        messages=messages,
        functions=functions,
        function_call=function_call,
        response_model=response_model,
        **kwargs,
    )

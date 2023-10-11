from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from marvin._compat import model_copy, model_dump
from marvin.utilities.messages import Message
from pydantic import BaseModel, Field
from typing_extensions import Self

from .handlers import Request, Response, Turn

T = TypeVar(
    "T",
    bound=BaseModel,
)


class Conversation(BaseModel, Generic[T], extra="allow", arbitrary_types_allowed=True):
    turns: list[Turn[T]]
    model: Any

    def __getitem__(self, key: int) -> Turn[T]:
        return self.turns[key]

    @property
    def last_turn(self) -> Turn[T]:
        return self.turns[-1]

    @property
    def last_request(self) -> Optional[Request[T]]:
        return self.turns[-1][0] if self.turns else None

    @property
    def last_response(self) -> Optional[Response[T]]:
        return self.turns[-1][1] if self.turns else None

    @property
    def history(self) -> list[Message]:
        response: list[Message] = []
        if not self.turns:
            return response
        if self.last_request:
            response = self.last_request.messages or []
            if self.last_response:
                response.append(self.last_response.choices[0].message)
        return response

    def send(self, messages: list[Message], **kwargs: Any) -> Turn[T]:
        params = kwargs
        if self.last_request:
            params = model_dump(self.last_request, exclude={"messages"}) | kwargs

        turn = self.model.create(
            **params,
            messages=[
                *self.history,
                *messages,
            ],
        )
        self.turns.append(turn)
        return turn

    async def asend(self, messages: list[Message], **kwargs: Any) -> Turn[T]:
        params = kwargs
        if self.last_request:
            params = model_dump(self.last_request, exclude={"messages"}) | kwargs

        turn = await self.model.acreate(
            **params,
            messages=[
                *self.history,
                *messages,
            ],
        )
        self.turns.append(turn)
        return turn


class AbstractChatCompletion(
    BaseModel, Generic[T], ABC, extra="allow", arbitrary_types_allowed=True
):
    """
    A ChatCompletion object is responsible for exposing a create and acreate method,
    and for merging default parameters with the parameters passed to these methods.
    """

    defaults: dict[str, Any] = Field(default_factory=dict, exclude=True)

    def __call__(self: Self, **kwargs: Any) -> Self:
        """
        Create a new ChatCompletion object with new defaults computed from
        merging the passed parameters with the default parameters.
        """
        copy = model_copy(self)
        copy.defaults = self.defaults | kwargs
        return copy

    @abstractmethod
    def _serialize_request(self, request: Optional[Request[T]]) -> dict[str, Any]:
        """
        Serialize the request.
        This should be implemented by derived classes based on their specific needs.
        """
        pass

    @abstractmethod
    def _create_request(self, **kwargs: Any) -> Request[T]:
        """
        Prepare and return a request object.
        This should be implemented by derived classes.
        """
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> Any:
        """
        Parse the response based on specific needs.
        """
        pass

    def merge_with_defaults(self, **kwargs: Any) -> dict[str, Any]:
        """
        Merge the passed parameters with the default parameters.
        """
        return self.defaults | kwargs

    @abstractmethod
    def _send_request(self, **serialized_request: Any) -> Any:
        """
        Send the serialized request to the appropriate endpoint/service.
        Derived classes should implement this.
        """
        pass

    @abstractmethod
    async def _send_request_async(
        self, **serialized_request: Any
    ) -> Response[T]:  # noqa
        """
        Send the serialized request to the appropriate endpoint/service asynchronously.
        Derived classes should implement this.
        """
        pass

    def create(self, response_model: Optional[type] = None, **kwargs: Any) -> Turn[T]:
        """
        Create a completion synchronously.
        Derived classes can override this if they need to change the core logic.
        """
        request = self._create_request(**kwargs, response_model=response_model)
        serialized_request = self._serialize_request(request=request)
        response_data = self._send_request(**serialized_request)
        response = self._parse_response(response_data)

        return Turn(
            request=Request(
                **serialized_request
                | self.defaults
                | model_dump(request, exclude_none=True)
                | ({"response_model": response_model} if response_model else {})
            ),
            response=response,
        )

    async def acreate(
        self, response_model: Optional[type[T]] = None, **kwargs: Any
    ) -> Turn[T]:
        """
        Create a completion asynchronously.
        Similar to the synchronous version but for async implementations.
        """
        request = self._create_request(**kwargs, response_model=response_model)
        serialized_request = self._serialize_request(request=request)
        response_data = await self._send_request_async(**serialized_request)
        response = self._parse_response(response_data)
        return Turn(
            request=Request(
                **serialized_request
                | self.defaults
                | model_dump(request, exclude_none=True)
                | ({"response_model": response_model} if response_model else {})
            ),
            response=response,
        )

    def chain(self, **kwargs: Any) -> Conversation[T]:
        """
        Create a new Conversation object.
        """
        with self as conversation:
            conversation.send(**kwargs)
            while conversation.last_turn.has_function_call():
                message = conversation.last_turn.call_function()
                conversation.send(
                    message if isinstance(message, list) else [message],
                )

            return conversation

    async def achain(self, **kwargs: Any) -> Conversation[T]:
        """
        Create a new Conversation object asynchronously.
        """
        with self as conversation:
            await conversation.asend(**kwargs)
            while conversation.last_turn.has_function_call():
                message = conversation.last_turn.call_function()
                await conversation.asend(
                    message if isinstance(message, list) else [message],
                )

            return conversation

    def __enter__(self: Self) -> Conversation[T]:
        """
        Enter a context manager.
        """
        return Conversation(turns=[], model=self)

    def __exit__(self: Self, *args: Any) -> None:
        """
        Exit a context manager.
        """
        pass

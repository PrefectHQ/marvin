from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from .ChatCompletion import BaseChatCompletion
from .messages import Message
from .requests import Request
from .responses import Response, Turn


class Conversation(BaseModel):
    model: "BaseChatCompletion" = Field(..., exclude=True, repr=False)
    turns: list[Turn] = Field(default_factory=list)

    @property
    def prompt_tokens(self) -> int:
        return sum(turn.response.prompt_tokens for turn in self.turns)

    @property
    def completion_tokens(self) -> int:
        return sum(turn.response.completion_tokens for turn in self.turns)

    @property
    def total_tokens(self) -> int:
        return sum(turn.response.total_tokens for turn in self.turns)

    @property
    def last(self) -> Turn:
        return self.turns[-1] if self.turns else Turn()

    @property
    def last_request(self) -> Request:
        return self.last.request

    @property
    def last_response(self) -> Response:
        return self.last.response

    @property
    def next_messages(
        self,
    ) -> list[Message]:
        messages: list[Message] = []
        if self.last.request.messages:
            messages.extend(self.last.request.messages)
        if self.last.response.message:
            messages.append(self.last.response.message)
        return messages

    def send(
        self,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> "Conversation":
        # Merge the messages from the last request.
        chat_completion = self.model(self.last.request)(
            messages=(
                [self.last.response.message] if self.last.response.message else []
            ),  # noqa
        )(
            messages=messages or [],
        )(
            functions=functions or self.last.request.functions,
            function_call=function_call or self.last.request.function_call,
            response_model=response_model or self.last.request.response_model,
        )
        self.turns.append(chat_completion.create())
        return self

    async def asend(
        self,
        messages: list[Message] | None = None,
        functions: list[Callable[..., Any] | dict[str, Any] | type[BaseModel]]
        | None = None,
        function_call: Literal["auto"] | dict[Literal["name"], str] | None = None,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> "Conversation":
        # Merge the messages from the last request.
        chat_completion = self.model(self.last.request)(
            messages=(
                [self.last.response.message] if self.last.response.message else []
            ),  # noqa
        )(
            messages=messages or [],
        )(
            functions=functions or self.last.request.functions,
            function_call=function_call or self.last.request.function_call,
            response_model=response_model or self.last.request.response_model,
        )
        self.turns.append(await chat_completion.acreate())
        return self

import inspect
from typing import Any, Awaitable, Callable, ClassVar, Optional, Type

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Extra, Field, root_validator

from ..utilities.async_utils import run_sync
from .messages import FunctionCall, Message
from .providers.openai import OpenAIResponseParser
from .requests import Request
from .serializers import AbstractResponseParser


class Response(BaseModel):
    parser: ClassVar[AbstractResponseParser] = OpenAIResponseParser()
    message: Optional[Message] = Field(default=None)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @root_validator(pre=True, allow_reuse=True)
    def parse_raw_response(cls, values: dict[str, Any]):
        return cls.parser.parse(**values)

    @property
    def function_call(self) -> Optional[FunctionCall]:
        return self.message.function_call if self.message else None

    @property
    def has_function_call(self) -> bool:
        return bool(self.function_call)

    @property
    def content(self) -> Optional[str]:
        return self.message.content if self.message else None

    class Config:
        extra = Extra.allow


class Turn(BaseModel):
    request: Request = Field(default_factory=Request)
    response: Response = Field(default_factory=Response)

    def has_function_call(self) -> bool:
        return bool(self.response.function_call)

    def has_response_model(self) -> bool:
        return bool(self.request.response_model)

    def _evaluate_function(self) -> Any:
        if self.response.message and self.response.message.function_call:
            name: str = self.response.message.function_call.name
            functions: dict[
                str,
                Optional[
                    Type[BaseModel] | Callable[..., Any] | Callable[..., Awaitable[Any]]
                ],
            ] = {
                fn.__name__: fn
                for fn in [
                    *(self.request.functions or []),
                    *([self.request.response_model] or []),
                ]
                if callable(fn)
            }
            if function := functions.get(name, None):
                if inspect.iscoroutinefunction(function):
                    promise: Awaitable[Any] = function(
                        **self.response.message.function_call.arguments
                    )  # noqa
                    return run_sync(promise)
                else:
                    return function(**self.response.message.function_call.arguments)
        else:
            return None

    def call_function(self, as_message: bool = True) -> Any | Message:
        if not self.response.message or not self.response.message.function_call:
            return None
        elif not as_message:
            evaluation: Any = self._evaluate_function()
            return evaluation
        else:
            evaluation: Any = self._evaluate_function()
            return Message(
                role="function",
                content=str(evaluation),
                name=getattr(self.response.message.function_call, "name", None),
            )

    def to_model(self) -> Optional[BaseModel]:
        if self.request.response_model:
            evaluation: BaseModel = self._evaluate_function()
            return evaluation
        else:
            return None

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "request": {
                **jsonable_encoder(self.request, exclude={"response_model"}),
                **self.request.serialize(),
            },
            "response": jsonable_encoder(self.response),
        }

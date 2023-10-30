import inspect
import json
from types import FunctionType
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

from marvin._compat import BaseModel, Field, ValidationError, cast_to_json, model_dump
from marvin.utilities.async_utils import run_sync
from marvin.utilities.logging import get_logger
from marvin.utilities.messages import Message, Role
from typing_extensions import ParamSpec

from .utils import parse_raw

T = TypeVar(
    "T",
    bound=BaseModel,
)

P = ParamSpec("P")


class Request(BaseModel, Generic[T], extra="allow", arbitrary_types_allowed=True):
    messages: Optional[list[Message]] = Field(default=None)
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
                    functions_serializer(function) for function in self.functions
                ]
            }
            if self.function_call:
                functions["function_call"] = self.function_call

        return extras | functions | function_call | messages | response_model

    def function_registry(self) -> dict[str, FunctionType]:
        return {
            function.__name__: function
            for function in self.functions or []
            if callable(function)
        }


class Choice(BaseModel):
    message: Message
    index: int
    finish_reason: str

    class Config:
        arbitrary_types_allowed = True


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

    def call_function(self) -> Union[Message, list[Message]]:
        if not self.has_function_call():
            raise ValueError("No function call found.")

        pairs: list[tuple[str, dict[str, Any]]] = self.get_function_call()
        function_registry: dict[str, FunctionType] = self.request.function_registry()
        evaluations: list[Any] = []

        logger = get_logger("ChatCompletion.handlers")

        for pair in pairs:
            name, argument = pair
            if name not in function_registry:
                raise ValueError(
                    f"Function {name} not found in {function_registry=!r}."
                )

            logger.debug_kv(
                "Function call",
                (
                    f"Calling function {name!r} with payload:"
                    f" {json.dumps(argument, indent=2)}"
                ),
                key_style="green",
            )

            function_result = function_registry[name](**argument)

            if inspect.isawaitable(function_result):
                function_result = run_sync(function_result)

            logger.debug_kv(
                "Function call",
                f"Function {name!r} returned: {function_result}",
                key_style="green",
            )

            evaluations.append(function_result)
        if len(evaluations) != 1:
            return [
                Message(
                    name=pairs[j][0],
                    role=Role.FUNCTION_RESPONSE,
                    content=str(evaluations[j]),
                    function_call=None,
                )
                for j in range(len(evaluations))
            ]
        else:
            return Message(
                name=pairs[0][0],
                role=Role.FUNCTION_RESPONSE,
                content=str(evaluations[0]),
                function_call=None,
            )

    def to_model(self, model_cls: Optional[type[T]] = None) -> T:
        model = model_cls or self.request.response_model

        if not model:
            raise ValueError("No model found.")

        pairs = self.get_function_call()
        try:
            return model(**pairs[0][1])
        except TypeError:
            pass
        except ValidationError:  # added this
            return model(output=pairs[0][1])
        try:
            return model.parse_raw(pairs[0][1])
        except TypeError:
            pass
        return model.construct(**pairs[0][1])

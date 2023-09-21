from types import FunctionType
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    overload,
)

from marvin._compat import cast_to_json, model_dump
from pydantic import BaseModel, Field

from .utils import parse_raw

T = TypeVar(
    "T",
    bound=BaseModel,
)

P = ParamSpec("P")


class FunctionCall(BaseModel):
    name: str
    arguments: str


class Message(BaseModel):
    content: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    function_call: Optional[FunctionCall] = Field(default=None)


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

    def call_function(self) -> Union[Message, list[Message]]:
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
        if len(evaluations) != 1:
            return [
                Message(
                    name=pairs[j][0],
                    role="function",
                    content=str(evaluations[j]),
                    function_call=None,
                )
                for j in range(len(evaluations))
            ]
        else:
            return Message(
                name=pairs[0][0],
                role="function",
                content=str(evaluations[0]),
                function_call=None,
            )

    def to_model(self) -> T:
        if not self.request.response_model:
            raise ValueError("No response model found.")
        model = self.request.response_model
        pairs = self.get_function_call()
        return model(**pairs[0][1])

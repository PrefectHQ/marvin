from typing import Any, Callable, Generic, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated, Self

from marvin import settings

T = TypeVar("T", bound=BaseModel)


class ResponseFormat(BaseModel):
    type: str


LogitBias = dict[str, float]


class Function(BaseModel, Generic[T]):
    name: str
    description: Optional[str]
    parameters: dict[str, Any]

    model: Optional[type[T]] = Field(exclude=True, repr=False)
    python_fn: Optional[Callable[..., Any]] = Field(
        default=None,
        description="Private field that holds the executable function, if available",
        exclude=True,
        repr=False,
    )

    def validate_json(self: Self, json_data: str | bytes | bytearray) -> T:
        if self.model is None:
            raise ValueError("This Function was not initialized with a model.")
        return self.model.model_validate_json(json_data)


class Tool(BaseModel, Generic[T]):
    type: str
    function: Optional[Function[T]] = None


class ToolSet(BaseModel, Generic[T]):
    tools: Optional[list[Tool[T]]] = None
    tool_choice: Optional[Union[Literal["auto"], dict[str, Any]]] = None


class RetrievalTool(Tool[T]):
    type: str = Field(default="retrieval")


class CodeInterpreterTool(Tool[T]):
    type: str = Field(default="code_interpreter")


class FunctionCall(BaseModel):
    name: str


class BaseMessage(BaseModel):
    content: str
    role: str


class Grammar(BaseModel):
    logit_bias: Optional[LogitBias] = None
    max_tokens: Optional[Annotated[int, Field(strict=True, ge=1)]] = None
    response_format: Optional[ResponseFormat] = None


class Prompt(Grammar, ToolSet[T], Generic[T]):
    messages: list[BaseMessage] = Field(default_factory=list)


class ResponseModel(BaseModel):
    model: type
    name: str = Field(default="FormatResponse")
    description: str = Field(default="Response format")


class ChatRequest(Prompt[T]):
    model: str = Field(default=settings.openai.chat.completions.model)
    frequency_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    n: Optional[Annotated[int, Field(strict=True, ge=1)]] = 1
    presence_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    seed: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = False
    temperature: Optional[Annotated[float, Field(strict=True, ge=0, le=2)]] = 1
    top_p: Optional[Annotated[float, Field(strict=True, ge=0, le=1)]] = 1
    user: Optional[str] = None


class AssistantMessage(BaseMessage):
    id: str
    thread_id: str
    created_at: int
    assistant_id: Optional[str] = None
    run_id: Optional[str] = None
    file_ids: list[str] = []
    metadata: dict[str, Any] = {}


class Run(BaseModel, Generic[T]):
    id: str
    thread_id: str
    created_at: int
    status: str
    model: str
    instructions: Optional[str]
    tools: Optional[list[Tool[T]]] = None
    metadata: dict[str, str]

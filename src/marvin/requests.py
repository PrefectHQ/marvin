from typing import Any, Callable, Literal, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from marvin import settings
from marvin.utilities.pydantic import cast_callable_to_model


class LogitBias(BaseModel):
    bias: dict[int, float]


class ResponseFormat(BaseModel):
    type: str


class Tool(BaseModel):
    type: str


class Function(BaseModel):
    """
    A representation of a callable function. The actual Python function is
    stored as well.
    """

    name: str
    description: Optional[str]
    parameters: dict[str, Any]
    python_fn: Callable = Field(
        None,
        exclude=True,
        description="Private field that holds the executable function, if available",
    )

    @classmethod
    def from_function(cls, fn: Callable, name: str = None, description: str = None):
        model = cast_callable_to_model(fn)
        return cls(
            name=name or fn.__name__,
            description=description or fn.__doc__,
            parameters=model.schema(),
            python_fn=fn,
        )


class FunctionTool(Tool):
    type: Literal["function"] = "function"
    function: Function

    @classmethod
    def from_function(cls, fn: Callable, name: str = None, description: str = None):
        return cls(
            type="function",
            function=Function.from_function(fn=fn, name=name, description=description),
        )


class RetrievalTool(Tool):
    type: Literal["retrieval"] = "retrieval"


class CodeInterpreterTool(Tool):
    type: Literal["code_interpreter"] = "code_interpreter"


class FunctionCall(BaseModel):
    name: str


class BaseMessage(BaseModel):
    content: str
    role: str


class Prompt(BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    tools: Optional[list[FunctionTool]] = None
    tool_choice: Optional[Union[Literal["auto"], FunctionCall]] = None
    logit_bias: Optional[LogitBias] = None
    max_tokens: Optional[Annotated[int, Field(strict=True, ge=1)]] = None


class ChatRequest(Prompt):
    model: str = Field(default=settings.openai.chat.completions.model)
    frequency_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    n: Optional[Annotated[int, Field(strict=True, ge=1)]] = 1
    presence_penalty: Optional[
        Annotated[float, Field(strict=True, ge=-2.0, le=2.0)]
    ] = 0
    response_format: Optional[ResponseFormat] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = False
    temperature: Optional[Annotated[float, Field(strict=True, ge=0, le=2)]] = 1
    top_p: Optional[Annotated[float, Field(strict=True, ge=0, le=1)]] = 1
    user: Optional[str] = None
